import fnmatch
import logging
import re
from os.path import isfile
from typing import Callable, List, Pattern, Sequence, TextIO, Tuple

T_PARSER_CALLABLE = Callable[[str], Pattern]

logger = logging.getLogger(__name__)


def parse_wildcard_to_regex(pattern: str) -> Pattern:
    """Parses a wildcard pattern to a compiled regex object."""
    regex_pattern = fnmatch.translate(pattern)
    compiled_regex = re.compile(regex_pattern)
    return compiled_regex


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


def retrieve_ignore_patterns_from_files(
        instructions: Sequence[Tuple[str, bool]]) -> List[Pattern]:
    """
    Parses the content of a given list of paths to a list of regex patterns.

    >>> retrieve_ignore_patterns_from_files([
    ...    # this file is containing extended regex patterns,
    ...    # we set `use_wildcards` to False
    ...    ('.s3ignore', False),
    ...
    ...    # # this file is containing wildcards patterns,
    ...    # we set `use_wildcards` to True
    ...    ('.gitignore', True)
    ... ])
    """
    patterns = []

    for path, use_wildcards in instructions:
        if isfile(path):
            parser = parse_wildcard_to_regex if use_wildcards else re.compile
            new_patterns = retrieve_ignore_patterns(path, parser)
            patterns += new_patterns
        else:
            logger.warn('Ignore file %s does not exist.', path)

    return patterns
