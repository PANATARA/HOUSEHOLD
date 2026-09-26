from core.exceptions.base_exceptions import (
    BaseAPIException,
    ObjectNotFoundError,
)


class UserError(BaseAPIException):
    """Base exception for all errors related to users actions."""

    pass


class UserNotFoundError(UserError, ObjectNotFoundError):
    """Base exception for all errors related to users actions."""

    def __init__(self, message="The user could not be found"):
        self.message = message
        super().__init__(self.message)

        super().__init__(self.message)


class UserAlreadyExistsError(UserError):
    def __init__(self, message="User with this username already exists"):
        self.message = message
        super().__init__(self.message)
