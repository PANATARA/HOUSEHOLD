from core.exceptions.base_exceptions import ObjectNotFoundError


class UserError(Exception):
    """Base exception for all errors related to users actions."""

    pass


class UserNotFoundError(UserError, ObjectNotFoundError):
    """Base exception for all errors related to users actions."""

    pass
