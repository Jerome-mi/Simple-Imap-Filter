class BaseFilterElement(object):
    class CheckError(Exception):
        pass

    tokens = ("name", "component", "encrypted")
    pass
