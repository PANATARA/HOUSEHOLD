from core.exceptions.base_exceptions import ObjectNotFoundError


class ChoreCompletionError(Exception):
    """Base exception for all errors related to chore completion actions."""

    pass


class ChoreCompletionNotFoundError(ChoreCompletionError, ObjectNotFoundError):
    def __init__(self, message="The specified chore completion was not found"):
        super().__init__(message)


class ChoreCompletionCanNotBeChanged(ChoreCompletionError):
    def __init__(self, message="The specified chore completion can't be cahnged"):
        super().__init__(message)
