class ExpressException(Exception):
    pass


class NoConfigFound(ExpressException):
    pass


class ListingDoesNotExist(ExpressException):
    pass
