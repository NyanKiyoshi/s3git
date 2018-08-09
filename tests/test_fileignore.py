import re
from unittest import mock

import pytest

from s3git.fileignore import (
    REGEX_PARSER, compile_ignore_file, get_parser, retrieve_ignore_patterns,
    wildcard_to_regex_parser)


@pytest.mark.parametrize('use_wildcard,expected', (
    (True, wildcard_to_regex_parser), (False, REGEX_PARSER)))
def test_get_parser(use_wildcard, expected):
    assert get_parser(use_wildcard) == expected


def test_parse_wildcard_to_regex():
    pattern = '*.pyc'
    regex = wildcard_to_regex_parser(pattern)
    assert not regex.match('hello.py')
    assert regex.match('hello.pyc')


def test_retrieve_ignore_patterns_with_wildcards(wildcard_s3ignore_file):
    instruction_count, fp = wildcard_s3ignore_file
    parser = wildcard_to_regex_parser

    with mock.patch('s3git.fileignore.open', create=True) as mocked_open:
        mocked_open.return_value = fp
        patterns = retrieve_ignore_patterns('', parser)
    assert len(patterns) == instruction_count


def test_retrieve_ignore_patterns_with_extended_regexes(regex_s3ignore_file):
    instruction_count, fp = regex_s3ignore_file
    parser = REGEX_PARSER

    with mock.patch('s3git.fileignore.open', create=True) as mocked_open:
        mocked_open.return_value = fp
        patterns = retrieve_ignore_patterns('', parser)
    assert len(patterns) == instruction_count


def test_compile_ignore_file_with_invalid_extended_regexes(
        invalid_regex_ignore_file):
    instruction_count, fp = invalid_regex_ignore_file
    parser = REGEX_PARSER

    with pytest.raises(re.error, message='Failed to parse: *\.py[cod]'):
        compile_ignore_file(fp, parser)
