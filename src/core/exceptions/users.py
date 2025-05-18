from core.exceptions.base_exceptions import (
    BaseAPIException,
    ImageError,
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


class UserAvatarSizeTooLargre(UserError, ImageError):
    def __init__(self, message="Image size is too large"):
        self.message = message
        super().__init__(self.message)


class UserAlreadyExistsError(UserError):
    def __init__(self, message="User with this username already exists"):
        self.message = message
        super().__init__(self.message)
