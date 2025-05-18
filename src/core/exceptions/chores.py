from core.exceptions.base_exceptions import BaseAPIException, ObjectNotFoundError


class ChoreError(BaseAPIException):
    """Base exception for all errors related to chores actions."""

    pass


class ChoreNotFoundError(ChoreError, ObjectNotFoundError):
    def __init__(self, message="The specified chore was not found."):
        super().__init__(message)
