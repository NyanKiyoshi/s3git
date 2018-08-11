import io
import os
import os.path

import boto3
import pytest

import git
from moto import mock_s3
from s3git.core import S3GitSync
from s3git.s3 import S3CONFIG_PATH, S3Bucket


@pytest.fixture
def binary_image():
    return b'GIF87a\x02\x00\x01\x00\x80\x02\x008(,L<@,' \
           b'\x00\x00\x00\x00\x02\x00\x01\x00\x00\x02\x02\x0c\n\x00;'


@pytest.fixture
def regex_s3ignore_file():
    instruction_count = 2
    fp = io.StringIO(
        r"""
        
        # Compiled python files
        [^\.]+\.pyc
        file\d{3}
        
        """)
    return instruction_count, fp


@pytest.fixture
def wildcard_s3ignore_file():
    instruction_count = 1
    fp = io.StringIO(
        r"""
        
        # Compiled python files
        *.py[cod]
        
        """)
    return instruction_count, fp


@pytest.fixture
def invalid_regex_ignore_file():
    instruction_count = 1
    fp = io.StringIO(
        r"""
        
        # Compiled python files
        *\.py[cod]
        
        """)
    return instruction_count, fp


@pytest.fixture(scope='function')
def test_files(tmpdir, binary_image):
    file_names = [
        'text-file', 'image-file', '.s3ignore', 'python-file.py']
    tmpdir.join(file_names[0]).write('hello')
    tmpdir.join(file_names[1]).write_binary(binary_image)
    tmpdir.join(file_names[2]).write(r'^.*\.py$')
    tmpdir.join(file_names[3]).write(r'exit(1)')

    return file_names


@pytest.fixture(scope='function')
def s3git_tracked_files(test_files):
    # remove excluded file from sync (.s3ignore)
    test_files.pop()
    return test_files


@pytest.fixture(scope='function')
def git_repo(tmpdir, test_files):
    old_path = tmpdir.chdir()

    # initialize a git repo and create a 'master' branch
    repo = git.Repo.init()
    repo.index.add(test_files)
    repo.index.commit('empty commit')
    repo.create_head('master').checkout()

    # setup is done, test can now be run
    yield repo

    # teardown of the repo
    old_path.chdir()


@pytest.fixture
def _repo_config():
    return """\
[default]
S3_ACCESS_KEY_ID = id
S3_SECRET_ACCESS_KEY = secret
S3_BUCKET_NAME = testBucket

[hello]
S3_ACCESS_KEY_ID = hi_id
S3_SECRET_ACCESS_KEY = hi_secret
S3_BUCKET_NAME = hi_bucket
"""


@pytest.fixture
def s3git_unpatched(s3_bucket, git_repo, _repo_config):
    config_path = os.path.join(git_repo.working_dir, S3CONFIG_PATH)

    with open(config_path, 'w') as w:
        w.write(_repo_config)

    s3git_instance = S3GitSync(None)
    return s3git_instance


@pytest.fixture
def s3git(s3git_unpatched, mocker):
    # patches
    mocked_s3_commit = mocker.patch.object(
        s3git_unpatched, '_get_s3_current_commit')
    mocked_s3_commit.return_value = None
    return s3git_unpatched


@pytest.fixture
def diff_commit(git_repo, s3git_tracked_files):
    previous_tree = git_repo.active_branch.commit.tree

    file_deleted = s3git_tracked_files.pop()
    file_modified = s3git_tracked_files.pop()
    file_added = 'new-file'

    # delete the first file
    os.remove(file_deleted)

    # edit the second file
    with open(file_modified, 'wb') as fp:
        fp.write(b'Dummy')

    # add the third file
    with open(file_added, 'w') as fp:
        fp.write('Another dummy')
    git_repo.git.add(file_added)

    # commit the changes
    git_repo.git.add(u=True)
    new_tree = git_repo.index.commit('Various changes').tree

    diff = {
        'D': [file_deleted], 'M': [file_modified], 'A': [file_added]}
    return previous_tree, diff, new_tree


@pytest.fixture(autouse=True)
def _clear_caches():
    S3Bucket.CACHED_DATA = {}


@pytest.fixture(scope='function')
def s3_bucket():
    bucket_name = 'testBucket'

    mock = mock_s3()
    mock.start()

    s3 = boto3.resource('s3')
    s3.create_bucket(Bucket=bucket_name)

    s3bucket_instance = S3Bucket(S3_BUCKET_NAME=bucket_name)
    yield s3bucket_instance

    mock.stop()
