import io
import pytest


@pytest.fixture
def s3ignore_file():
    instruction_count = 2
    fp = io.StringIO(
        r"""
        
        # Compiled python files
        [^\.]+\.pyc
        file\d{3}
        
        """)
    return instruction_count, fp


@pytest.fixture
def gitignore_file():
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
