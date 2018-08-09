from unittest import mock

import pytest

from s3git.core import (
    IGNORE_FILE_PATH, W_DIRTY_REPO_MSG, W_INEXISTING_IGNORE_FILE,
    _retrieve_ignore_list, get_repo, logger)
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
