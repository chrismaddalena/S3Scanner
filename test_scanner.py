import s3utils as s3
import sh
import os
import sys
import shutil

pyVersion = sys.version_info
# pyVersion[0] can be 2 or 3


s3scannerLocation = "./"
testingFolder = "./test/"


def test_arguments():
    # Scenario 1: No arguments

    try:
        sh.python(s3scannerLocation + 's3scanner.py')
    except sh.ErrorReturnCode as e:
        assert e.stderr.decode('utf-8') == ""
        assert "usage: s3scanner [-h] [-o OUTFILE] [-c] [-r] [-d] buckets" in e.stdout.decode('utf-8')


def test_checkBucket():
    """
    Scenario 1: Bucket name exists, region is wrong
        Expected:
            Code: 301
            Region: Region returned depends on the closest S3 region to the user. Since we don't know this,
                    just assert for 2 hyphens.
        Note:
            Amazon should always give us a 301 to redirect to the nearest s3 endpoint.
            Currently uses the ap-south-1 (Asia Pacific - Mumbai) region, so if you're running
            the test near there, change to a region far from
            you - https://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region

    Scenario 2: Bucket exists, region correct
        Expected:
            Code: 200
            Message: Contains the domain name and region
        Note:
            Using flaws.cloud as example by permission of owner (@0xdabbad00)

    """
    # Scenario 1
    result = s3.checkBucket('amazon.com', 'ap-south-1')
    assert result[0] == 301
    assert result[1].count("-") == 2

    # Scenario 2
    result = s3.checkBucket('flaws.cloud', 'us-west-2')
    assert result[0] == 200
    assert result[1] == 'flaws.cloud'
    assert result[2] == 'us-west-2'


def test_checkIncludeClosed():
    """ Verify that the '--include-closed' argument is working correctly.
        Expected:
            The bucket name 'yahoo.com' is expected to exist, but be closed. The bucket name
            and region should be included in the output buckets file in the format 'bucket:region'.
    """

    # Create a file called testing.txt and write 'yahoo.com' to it

    inFile = testingFolder + 'test_checkIncludeClosed_in.txt'
    outFile = testingFolder + 'test_checkIncludeClosed_out.txt'

    f = open(inFile, 'w')
    f.write('yahoo.com\n')  # python will convert \n to os.linesep
    f.close()

    run1 = sh.python(s3scannerLocation + "s3scanner.py", "--out-file", outFile,
                     "--include-closed", inFile)

    found = False
    with open(outFile, 'r') as g:
        for line in g:
            if 'yahoo.com' in line:
                found = True

    try:
        assert found is True
    finally:
        # Cleanup testing files
        os.remove(outFile)
        os.remove(inFile)


def test_dumpBucket():
    """
        Verify the dumpBucket() function is working as intended.

        Expected: Supplying the function with the arguments ("flaws.cloud", "us-west-2") should result in 6 files
                being downloaded into the buckets folder. The expected file sizes of each file are listed in the
                'expectedFiles' dictionary.
    """

    # Dump the flaws.cloud bucket
    s3.dumpBucket("flaws.cloud", "us-west-2")

    # Folder to look for the files in
    dumpDir = './buckets/flaws.cloud/'

    # Expected sizes of each file
    expectedFiles = {'hint1.html': 2575, 'hint2.html': 1707, 'hint3.html': 1101, 'index.html': 2877,
                     'robots.txt': 46, 'secret-dd02c7c.html': 1051}

    try:
        # Assert number of files in the folder
        assert len(os.listdir(dumpDir)) == len(expectedFiles)

        # For each file, assert the size
        for file, size in expectedFiles.items():
            assert os.path.getsize(dumpDir + file) == size
    finally:
        # No matter what happens with the asserts, cleanup after the test by deleting the flaws.cloud directory
        shutil.rmtree(dumpDir)


def test_getBucketSize():
    """
    Scenario 1: Bucket doesn't exist
        Expected: 255

    Scenario 2: Bucket exists, listing open to public
        Expected:
            Size: 9.1 KiB
        Note:
            Using flaws.cloud as example by permission of owner (@0xdabbad00)

    """

    # Scenario 1
    try:
        result = s3.getBucketSize('example-this-hopefully-wont-exist-123123123')
    except sh.ErrorReturnCode_255:
        assert True

    # Scenario 3
    assert s3.getBucketSize('flaws.cloud') == "9.1 KiB"


def test_outputFormat():
    """
    Scenario:
        Verify that the main script outputs found buckets in the format "bucket:region"
    Expected:
        The output for flaws.cloud should be the following: "flaws.cloud:us-west-2"
    """

    inFile = testingFolder + 'test_outputFormat_in.txt'
    outFile = testingFolder + 'test_outputFormat_out.txt'

    f = open(inFile, 'w')
    f.write('flaws.cloud\n')  # python will convert \n to os.linesep
    f.close()

    sh.python(s3scannerLocation + '/s3scanner.py', '--out-file', outFile, inFile)

    found = False
    with open(outFile, 'r') as g:
        for line in g:
            if line.strip() == 'flaws.cloud:us-west-2':
                found = True

        try:
            assert found is True
        finally:
            # Cleanup testing files
            os.remove(outFile)
            os.remove(inFile)
