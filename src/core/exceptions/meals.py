from core.exceptions.base_exceptions import BaseAPIException, ObjectNotFoundError


class MealError(BaseAPIException):
    """Base exception for all errors related to meals and recipes."""

    pass


class RecipeNotFoundError(MealError, ObjectNotFoundError):
    def __init__(self, message="The specified recipe was not found."):
        super().__init__(message)


class PlannedMealNotFoundError(MealError, ObjectNotFoundError):
    def __init__(self, message="The specified planned meal was not found."):
        super().__init__(message)


class GroceryItemNotFoundError(MealError, ObjectNotFoundError):
    def __init__(self, message="The specified grocery item was not found."):
        super().__init__(message)
