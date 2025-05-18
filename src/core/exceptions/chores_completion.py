from core.exceptions.base_exceptions import (
    BaseAPIException,
    CanNotBeChangedError,
    ObjectNotFoundError,
)


class ChoreCompletionError(BaseAPIException):
    """Base exception for all errors related to chore completion actions."""

    pass


class ChoreCompletionNotFoundError(ChoreCompletionError, ObjectNotFoundError):
    def __init__(self, message="The specified chore completion was not found"):
        super().__init__(message)


class ChoreCompletionCanNotBeChanged(ChoreCompletionError, CanNotBeChangedError):
    def __init__(self, message="The specified chore completion can't be cahnged"):
        super().__init__(message)


class ChoreCompletionIsNotApproved(ChoreCompletionError, CanNotBeChangedError):
    def __init__(self, message="The specified chore completion is not approved"):
        super().__init__(message)
