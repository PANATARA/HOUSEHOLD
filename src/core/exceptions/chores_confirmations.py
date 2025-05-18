from core.exceptions.base_exceptions import BaseAPIException, CanNotBeChangedError


class ChoreConfirmationError(BaseAPIException):
    """Base exception for all errors related to chore completion actions."""

    pass


class ChoreConfiramtionCanNotBeCahnged(ChoreConfirmationError, CanNotBeChangedError):
    def __init__(self, message="The specified chore confirmation can't be cahnged"):
        super().__init__(message)
