import logging
import os
import os.path
from io import BytesIO
from typing import Pattern, Union

from git import InvalidGitRepositoryError, Repo, Tree
from s3git.exceptions import *
from s3git.fileignore import get_parser, retrieve_ignore_patterns
from s3git.s3 import S3Bucket

REV_FILE_NAME = '.s3git-rev'


logger = logging.getLogger(__name__)

IGNORE_FILE_PATH = os.getenv('IGNORE_FILE_PATH', '.s3ignore')

W_INEXISTING_IGNORE_FILE = 'Ignore file %s does not exist.'
W_DIRTY_REPO_MSG = 'The repository contains uncommitted ' \
                   'changes that will not be synced.'


def _retrieve_ignore_list(use_wildcard):
    path = IGNORE_FILE_PATH
    parser = get_parser(use_wildcard)

    if os.path.isfile(path):
        ignore_list = retrieve_ignore_patterns(path, parser)
    else:
        ignore_list = []
        logger.warn(W_INEXISTING_IGNORE_FILE, path)

    return ignore_list


def get_repo():
    path = os.getcwd()

    try:
        repo = Repo(path)
    except InvalidGitRepositoryError as exc:
        raise InvalidRepository(path) from exc

    if repo.is_dirty():
        logger.warn(W_DIRTY_REPO_MSG)

    return repo


class S3GitSync:
    def __init__(
            self,
            branch: Union[str, None],
            force_reupload=False, use_wildcard=False):

        self.repo = get_repo()

        # if no branch or revision to sync from was passed,
        # we set to sync from the current branch
        if not branch:
            branch = self.repo.active_branch.name

        # TODO: remove this, it is unused
        self.branch = branch

        self.s3_settings = S3Bucket.read_config(branch)
        self.ignore_list = _retrieve_ignore_list(use_wildcard)

        self.old_tree = self.get_empty_tree() \
            if force_reupload else self.get_remote_tree()
        self.target_tree = self.get_tree(self.repo.commit(branch))

    def _get_s3_current_commit(self):
        fp = self.s3_settings.get_file(REV_FILE_NAME)

        if fp:
            commit = fp.readline().decode()
            return commit
        return None

    def is_ignored(self, file):
        for pattern in self.ignore_list:  # type: Pattern
            if pattern.match(file):
                return True
        return False

    def get_empty_tree(self):
        return self.get_tree(
            self.repo.git.hash_object('-w', '-t', 'tree', os.devnull))

    def get_tree(self, commit):
        return self.repo.tree(commit)

    def get_remote_tree(self):
        """
        Gets the SHA1 commit value of the S3 storage bucket
        or `None` if the bucket doesn't have one
        (implies we are starting on a clean tree).
        """
        current_s3_commit = self._get_s3_current_commit()

        if current_s3_commit:
            return self.get_tree(current_s3_commit)
        return self.get_empty_tree()

    def _get_file_content(self, sha1_hash, file):
        content_str = self.repo.git.show('%s:%s' % (sha1_hash, file))
        fp = BytesIO(content_str.encode(errors='surrogateescape'))
        return fp

    def _get_diffs(self):
        diffs = self.repo.git.diff(
            '--name-status', '--no-renames', '-z',
            self.old_tree.hexsha, self.target_tree.hexsha)
        diffs = iter(diffs.split('\0'))

        # Diffs will be stored as {status: [file1, ..., file_n]}
        # The aim is to make bulk requests to the API
        results = {}

        for entry in diffs:
            if not entry:
                continue

            status, file = entry, next(diffs)

            if status not in ['A', 'M', 'D']:
                raise UnexpectedDiffStatus(status)

            if self.is_ignored(file):
                continue

            results.setdefault(status, [])
            results[status].append(file)

            logger.info('[%s] %s', status, file)

        return results

    def _upload_diffs(self, status, target_paths):
        if status in ['A', 'M']:
            for path in target_paths:
                fp = self._get_file_content(self.target_tree, path)
                try:
                    self.s3_settings.upload(fp, path)
                finally:
                    fp.close()
        elif status == 'D':
            logger.info('Instructing to delete %d files', len(target_paths))
            self.s3_settings.delete_files(target_paths)
        else:
            raise UnexpectedDiffStatus(status)

    def _upload_new_commit_value(self):
        with BytesIO(self.target_tree.hexsha.encode()) as fp:
            self.s3_settings.upload(fp, REV_FILE_NAME)

    def synchronize(self):
        logger.info(
            'Starting to sync from {} to {}'.format(
                self.old_tree, self.target_tree))

        if self.old_tree == self.target_tree:
            raise RemoteUpToDate(())

        for status, target_paths in self._get_diffs().items():
            self._upload_diffs(status, target_paths)

        self._upload_new_commit_value()
