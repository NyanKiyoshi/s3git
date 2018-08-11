import fnmatch
import logging
import re
from os.path import isfile
from typing import Callable, List, Pattern, Sequence, TextIO, Tuple

T_PARSER_CALLABLE = Callable[[str], Pattern]
REGEX_PARSER = re.compile

logger = logging.getLogger(__name__)


def wildcard_to_regex_parser(pattern: str) -> Pattern:
    """Parses a wildcard pattern to a compiled regex object."""
    regex_pattern = fnmatch.translate(pattern)
    compiled_regex = REGEX_PARSER(regex_pattern)
    return compiled_regex


def get_parser(use_wildcard):
    return wildcard_to_regex_parser if use_wildcard else REGEX_PARSER


def compile_ignore_file(
        fp: TextIO, parser: T_PARSER_CALLABLE) -> List[Pattern]:
    """
    Reads every line of a given file object to process,
    and converts those lines to a compiled regex
    (except lines that are comments or empty).
    """
    patterns = []

    line = fp.readline()
    while line:
        line = line.strip()

        # if the line is not empty and not a comment, parse it.
        if line and not line.startswith('#'):
            try:
                compiled_regex = parser(line)
            except Exception as exc:
                raise exc.__class__('Failed to parse: %s' % line) from exc
            patterns.append(compiled_regex)

        line = fp.readline()

    return patterns


def retrieve_ignore_patterns(
        path: str, parser: T_PARSER_CALLABLE) -> List[Pattern]:
    """
    Assumes that the given path:
        - exists;
        - is a file.

    This function opens the path and compiles
    every line containing a pattern to a compiled regex using `parser`.

    And then returns the found patterns as a list of regex.
    """
    with open(path) as fp:
        patterns = compile_ignore_file(fp, parser)
        return patterns
