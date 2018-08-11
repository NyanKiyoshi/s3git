import os
from hashlib import sha1
from unittest import mock

import pytest

from s3git.core import S3GitSync


@mock.patch('s3git.s3.S3Bucket.read_config')
@mock.patch.object(S3GitSync, '_get_s3_current_commit')
def test__init__without_given_branch(mocked_s3_commit, _, git_repo):
    mocked_s3_commit.return_value = None

    branch = None
    s3git = S3GitSync(branch)
    assert s3git.branch == 'master'


@mock.patch('s3git.s3.S3Bucket.read_config')
@mock.patch.object(S3GitSync, '_get_s3_current_commit')
def test__init__with_given_branch(mocked_s3_commit, _, git_repo):
    mocked_s3_commit.return_value = None

    branch = 'hello'
    git_repo.create_head(branch)
    s3git = S3GitSync(branch)
    assert s3git.branch == branch


@mock.patch('s3git.s3.S3Bucket.read_config')
@mock.patch.object(S3GitSync, 'get_empty_tree')
@mock.patch.object(S3GitSync, 'get_remote_tree')
@pytest.mark.parametrize(
    'force_reupload,get_empty_tree_calls,get_remote_tree_calls', (
        (True, 1, 0), (False, 0, 1)))
def test__init__force_reupload_takes_correct_tree(
        mocked_get_remote_tree, mocked_get_empty_tree, _, git_repo,
        force_reupload, get_empty_tree_calls, get_remote_tree_calls):

    S3GitSync(None, force_reupload=force_reupload)
    assert mocked_get_remote_tree.call_count == get_remote_tree_calls
    assert mocked_get_empty_tree.call_count == get_empty_tree_calls


def test__get_file_content_handles_binary_files(s3git):
    s3git = S3GitSync(None)

    with open('image-file', 'rb') as fp:
        expected_sha1 = sha1(fp.read()).hexdigest()

    read_file = s3git._get_file_content(s3git.branch, 'image-file')
    receive_file_sha1 = sha1(read_file.read()).hexdigest()

    assert receive_file_sha1 == expected_sha1


@mock.patch('s3git.core.logger')
def test__get_diffs_with_empty_tree(_, s3git, git_repo, s3git_tracked_files):
    expected_diff = {'A': sorted(s3git_tracked_files)}
    assert s3git._get_diffs() == expected_diff


@mock.patch('s3git.core.logger')
def test__get_diffs_without_empty_tree(_, s3git, git_repo, diff_commit):
    old_tree, expected_diff, new_tree = diff_commit
    s3git.old_tree, s3git.target_tree = old_tree, new_tree

    assert s3git._get_diffs() == expected_diff


@mock.patch('s3git.core.logger')
def test__get_diffs_with_dirty_tree(_, s3git, git_repo, s3git_tracked_files):
    s3git.old_tree = git_repo.active_branch.commit.tree

    file_deleted = s3git_tracked_files.pop()
    file_modified = s3git_tracked_files.pop()

    os.remove(file_deleted)
    open(file_modified, 'wb').close()

    expected_diff = {}
    git_repo.git.add(u=True)

    assert s3git._get_diffs() == expected_diff
