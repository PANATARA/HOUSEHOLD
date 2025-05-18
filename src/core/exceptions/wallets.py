from core.exceptions.base_exceptions import BaseAPIException, ObjectNotFoundError


class WalletError(BaseAPIException):
    """Base exception for all errors related to wallet actions."""

    pass


class WalletNotFoundError(WalletError, ObjectNotFoundError):
    def __init__(self, message="User does not have enough coins for the transaction."):
        super().__init__(message)


class NotEnoughCoins(WalletError):
    def __init__(self, message="User does not have enough coins for the transaction."):
        super().__init__(message)
