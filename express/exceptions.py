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


class MissingBackpackAPIKey(ExpressException):
    pass


class MissingSTNAPIKey(ExpressException):
    pass


class MissingAIAPIKey(ExpressException):
    pass


class NoKeyPrice(ExpressException):
    pass


class WrongPriceFormat(ExpressException):
    pass


class NoArbitrageModuleFound(ExpressException):
    pass
