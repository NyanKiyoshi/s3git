class cached_property(object):
    def __init__(self, f):
        self._fname = f.__name__
        self._f = f

    def __get__(self, obj, owner):
        assert obj is not None, 'call {} on an instance'.format(self._fname)
        ret = obj.CACHED_DATA[self._fname] = self._f(obj)
        return ret
