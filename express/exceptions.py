class ExpressException(Exception):
    pass


class NoConfigFound(ExpressException):
    pass


class ListingDoesNotExist(ExpressException):
    pass


class SKUNotFound(ExpressException):
    pass


class MissingBackpackTFToken(ExpressException):
    pass
