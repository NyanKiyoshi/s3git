from typing import Dict, IO

T_RULES = Dict[str, IO]


class _FakeOpen:
    rules = None

    def __init__(self, path):
        if path in self.rules:
            self.fp = self.rules[path]
        else:
            raise ValueError('Got an unexpected path: %s' % path)

    def __enter__(self):
        return self.fp

    def __exit__(self, *_):
        pass


def fake_opener(rules: T_RULES) -> _FakeOpen:
    cls = _FakeOpen
    new_cls = type(cls)(cls.__name__, (cls,), {'rules': rules})
    return new_cls
