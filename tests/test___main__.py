import os
from unittest import mock

import pytest

from s3git.__main__ import main
from s3git.exceptions import BaseError, MissingConfigurationFile
from s3git.s3 import S3CONFIG_PATH


@mock.patch('s3git.__main__.S3GitSync', autospec=True)
@pytest.mark.parametrize('argv,expected_kwargs', (
    (['s3git'], {
        'branch': None, 'force_reupload': False, 'use_wildcard': False}),
    (['s3git', 'master'], {
        'branch': 'master', 'force_reupload': False, 'use_wildcard': False}),
    (['s3git', '-f', '-w', 'master'], {
        'branch': 'master', 'force_reupload': True, 'use_wildcard': True})))
def test_main_command_lines_arguments(mocked_S3GitSync, argv, expected_kwargs):
    with mock.patch('s3git.__main__.argv', new=argv, create=True):
        main()

    s3git_instance = mocked_S3GitSync.return_value
    mocked_S3GitSync.assert_called_once_with(**expected_kwargs)
    s3git_instance.synchronize.assert_called_once_with()


@mock.patch('s3git.__main__.argv', new=['s3git'], create=True)
@mock.patch('s3git.__main__.logger.error', autospec=True)
@mock.patch.object(BaseError, 'MSG', new='Ooopsie.')
def test_main_handles_internal_exceptions(mocked_error):
    def _wrapper(*args, **kwargs):
        raise BaseError(())

    with mock.patch('s3git.__main__.S3GitSync.__init__', new=_wrapper):
        with pytest.raises(SystemExit, message=1):
            main()

    mocked_error.assert_called_once_with('Ooopsie.')


@mock.patch('s3git.__main__.argv', new=['s3git'], create=True)
@mock.patch('s3git.__main__.logger.error', autospec=True)
def test_main_missing_s3config_file_raises_error(mocked_error, s3git):
    os.remove(S3CONFIG_PATH)
    with pytest.raises(SystemExit, message=1):
        main()

    mocked_error.assert_called_once_with(
        MissingConfigurationFile.MSG % S3CONFIG_PATH)
