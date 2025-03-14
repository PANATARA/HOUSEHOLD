from core.exceptions.base_exceptions import ObjectNotFoundError


class ProductError(Exception):
    """Base exception for all errors related to product actions."""

    pass


class ProductNotFoundError(ProductError, ObjectNotFoundError):
    def __init__(self, message="The specified product was not found."):
        super().__init__(message)
