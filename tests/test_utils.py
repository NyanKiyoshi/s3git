from s3git.utils import cached_property


def test_cached_property():
    class TestClass:
        __slots__ = '_a',
        CACHED_DATA = {}

        def __init__(self):
            self._a = 1

        @cached_property
        def a(self):
            return self._a

    instance = TestClass()
    assert instance.a == 1

    instance._a = 2
    assert instance.a == 1
