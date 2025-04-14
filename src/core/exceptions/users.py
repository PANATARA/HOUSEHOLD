from core.exceptions.base_exceptions import ImageError, ObjectNotFoundError


class UserError(Exception):
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
