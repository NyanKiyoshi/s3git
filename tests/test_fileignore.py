import re
import pytest
from unittest import mock

from s3git.fileignore import (
    parse_wildcard_to_regex, retrieve_ignore_patterns,
    retrieve_ignore_patterns_from_files, compile_ignore_file)
from tests.utils import fake_opener


def test_parse_wildcard_to_regex():
    pattern = '*.pyc'
    regex = parse_wildcard_to_regex(pattern)
    assert not regex.match('hello.py')
    assert regex.match('hello.pyc')


def test_retrieve_ignore_patterns_with_wildcards(gitignore_file):
    instruction_count, fp = gitignore_file
    parser = parse_wildcard_to_regex

    with mock.patch('s3git.fileignore.open', create=True) as mocked_open:
        mocked_open.return_value = fp
        patterns = retrieve_ignore_patterns('', parser)
    assert len(patterns) == instruction_count


def test_retrieve_ignore_patterns_with_extended_regexes(s3ignore_file):
    instruction_count, fp = s3ignore_file
    parser = re.compile

    with mock.patch('s3git.fileignore.open', create=True) as mocked_open:
        mocked_open.return_value = fp
        patterns = retrieve_ignore_patterns('', parser)
    assert len(patterns) == instruction_count


def test_compile_ignore_file_with_invalid_extended_regexes(
        invalid_regex_ignore_file):
    instruction_count, fp = invalid_regex_ignore_file
    parser = re.compile

    with pytest.raises(re.error, message='Failed to parse: *\.py[cod]'):
        compile_ignore_file(fp, parser)


@mock.patch('s3git.fileignore.isfile')
@mock.patch('s3git.fileignore.retrieve_ignore_patterns')
def test_retrieve_ignore_patterns_from_files(
        mocked_retrieve_ignore_patterns, mocked_isfile):

    mocked_isfile.return_value = True
    mocked_retrieve_ignore_patterns.return_value = []

    instructions_args = (
        ('mypath', True),
        ('mypath', False))

    expected_calls = [
        mock.call('mypath', parse_wildcard_to_regex),
        mock.call('mypath', re.compile)]

    retrieve_ignore_patterns_from_files(instructions_args)
    mocked_retrieve_ignore_patterns.assert_has_calls(expected_calls)


@mock.patch('s3git.fileignore.isfile')
def test_retrieve_ignore_patterns_from_files_correctly_selects_parser(
        mocked_isfile, gitignore_file, s3ignore_file):

    mocked_isfile.return_value = True

    gitignore_count, gitignore_fp = gitignore_file
    s3ignore_count, s3ignore_fp = s3ignore_file

    expected_pattern_count = gitignore_count + s3ignore_count

    instructions_args = (
        ('.gitignore', True),
        ('.fileignore', False))

    opener = fake_opener({
        '.gitignore': gitignore_fp, '.fileignore': s3ignore_fp})

    with mock.patch('s3git.fileignore.open', new=opener, create=True):
        patterns = retrieve_ignore_patterns_from_files(instructions_args)
        assert len(patterns) == expected_pattern_count


@mock.patch('s3git.fileignore.isfile')
@mock.patch('s3git.fileignore.logger.warn')
def test_retrieve_ignore_patterns_from_files_with_invalid_path(
        mocked_warn, mocked_isfile):
    mocked_isfile.return_value = False
    path = 'mypath'

    patterns = retrieve_ignore_patterns_from_files(((path, True),))

    mocked_isfile.assert_called_once_with(path)
    mocked_warn.assert_called_once_with('Ignore file %s does not exist.', path)
    assert not patterns
