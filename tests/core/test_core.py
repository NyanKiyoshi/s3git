from unittest import mock

import pytest

from s3git.core import (
    IGNORE_FILE_PATH, W_DIRTY_REPO_MSG, W_INEXISTING_IGNORE_FILE,
    _retrieve_ignore_list, get_repo, logger, REV_FILE_NAME)
from s3git.exceptions import *
from s3git.fileignore import get_parser


def test_get_repo_inexisting(tmpdir):
    """A non-existing repo should raise an error."""
    current_path = tmpdir.strpath
    tmpdir.chdir()
    with pytest.raises(
            InvalidRepository, message=InvalidRepository.MSG % current_path):
        get_repo()


@mock.patch.object(logger, 'warn')
def test_get_repo(mocked_logger, git_repo):
    """
    An existing repo should not raise an error.
    And not warn if the repo is clean.
    """
    get_repo()
    mocked_logger.assert_not_called()


@mock.patch.object(logger, 'warn')
def test_get_repo_dirty(mocked_logger, git_repo):
    """
    An existing repo should not raise an error.
    And should warn when the repo is dirty.
    """
    # edit a file in the repo, and don't commit it; to make it dirty
    open('text-file', 'w').close()

    # retrieve the dirty repo
    get_repo()

    # ensure it was detected and raised a warning
    mocked_logger.assert_called_once_with(W_DIRTY_REPO_MSG)


@mock.patch('os.path.isfile')
@mock.patch('s3git.core.retrieve_ignore_patterns')
@mock.patch('s3git.core.logger.warn')
@pytest.mark.parametrize('use_wildcard', (True, False))
def test__retrieve_ignore_list(
        mocked_warn,
        mocked_retrieve_ignore_patterns, mocked_isfile, use_wildcard):

    return_value = ['a']
    mocked_retrieve_ignore_patterns.return_value = return_value
    mocked_isfile.return_value = True

    assert _retrieve_ignore_list(use_wildcard) == return_value
    mocked_warn.assert_not_called()
    mocked_retrieve_ignore_patterns.assert_called_once_with(
        IGNORE_FILE_PATH, get_parser(use_wildcard))


@mock.patch('os.path.isfile')
@mock.patch('s3git.core.logger.warn')
def test__retrieve_ignore_list_warns_on_inexisting_ignore_file(
        mocked_warn, mocked_isfile):

    mocked_isfile.return_value = False

    assert _retrieve_ignore_list(False) == []
    mocked_warn.assert_called_once_with(
        W_INEXISTING_IGNORE_FILE, IGNORE_FILE_PATH)


def test__get_diffs_raises_on_invalid_status(s3git):
    s3git.repo = mock.MagicMock()
    s3git.repo.git.diff.return_value = 'H\0filename'
    with pytest.raises(UnexpectedDiffStatus, message='H'):
        s3git._get_diffs()


def test__upload_diffs_raises_on_invalid_status(s3git):
    with pytest.raises(UnexpectedDiffStatus, message='H'):
        s3git._upload_diffs('H', [])


def test__upload_new_commit_value(s3git_unpatched, s3_bucket):
    s3git = s3git_unpatched

    # Ensure there is no existing data in the s3 revision file
    remote_hash_value = s3_bucket.get_file(REV_FILE_NAME)
    assert not remote_hash_value

    # Get the current tree hash of the repo
    tree_sha1 = s3git.repo.tree(
        s3git.repo.active_branch.commit).hexsha

    # Upload the value to s3
    s3git._upload_new_commit_value()

    # Check the value was uploaded and correctly saved
    remote_hash_value = s3_bucket.get_file(REV_FILE_NAME)
    assert remote_hash_value.readline().decode() == tree_sha1
    assert s3git._get_s3_current_commit() == tree_sha1


def test_synchronize_from_empty_tree(
        s3git_unpatched, s3_bucket, s3git_tracked_files):

    s3git = s3git_unpatched
    s3git._upload_diffs = mock.MagicMock(
        wraps=s3git._upload_diffs, autospec=True)
    s3git._upload_new_commit_value = mock.MagicMock(
        wraps=s3git._upload_new_commit_value, autospec=True)

    # launch the synchronization
    s3git.synchronize()
    s3git._upload_new_commit_value.assert_called_once_with()
    s3git._upload_diffs.assert_called_once_with(
        'A', sorted(s3git_tracked_files))

    s3git._upload_new_commit_value.reset_mock()
    s3git._upload_diffs.reset_mock()

    # to remote repo should be up to date, there is nothing to sync anymore
    # thus nothing should happen, except raising an exception
    s3git.__init__(None)
    with pytest.raises(RemoteUpToDate):
        s3git.synchronize()
    assert not s3git._upload_new_commit_value.called
    assert not s3git._upload_diffs.called

    # check everything was correctly uploaded to s3
    for filename in s3git_tracked_files:
        remote_fp = s3_bucket.get_file(filename)
        assert remote_fp

        try:
            remote_data = remote_fp.read()
        finally:
            remote_fp.close()

        with open(filename, 'rb') as local_fp:
            assert remote_data == local_fp.read()


def test_synchronize_edited_tree(s3git_unpatched, s3_bucket, diff_commit):
    s3git = s3git_unpatched
    s3git.old_tree, diffs, s3git.target_tree = diff_commit

    mocked_upload_diffs = s3git._upload_diffs = mock.MagicMock(
        wraps=s3git._upload_diffs)
    s3git._upload_new_commit_value = mock.MagicMock(
        wraps=s3git._upload_new_commit_value)

    expected_calls = [
        mock.call(status, files) for status, files in diffs.items()]

    # launch the synchronization
    s3git.synchronize()

    # check everything was correctly called
    s3git._upload_new_commit_value.assert_called_once_with()
    mocked_upload_diffs.assert_has_calls(expected_calls, any_order=True)

    # check the s3 now has the new tree hash
    assert s3git.get_remote_tree().hexsha == s3git.target_tree.hexsha

    # check deleted files are deleted from s3
    for filename in diffs['D']:
        remote_fp = s3_bucket.get_file(filename)
        assert not remote_fp

    # check everything added was correctly uploaded and updated to s3
    for filename in diffs['A'] + diffs['M']:
        remote_fp = s3_bucket.get_file(filename)

        try:
            assert remote_fp
            remote_data = remote_fp.read()
        finally:
            remote_fp.close()

        with open(filename, 'rb') as local_fp:
            assert remote_data == local_fp.read()
