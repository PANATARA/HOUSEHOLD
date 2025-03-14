from core.exceptions.base_exceptions import ConflictError, ObjectNotFoundError


class FamilyError(Exception):
    """Base exception for all errors related to family actions."""

    pass


class FamilyNotFoundError(FamilyError, ObjectNotFoundError):
    def __init__(self, message="The family was not found."):
        super().__init__(message)


class UserNotFoundInFamily(FamilyError, ObjectNotFoundError):
    def __init__(self, message="No such user found in the family"):
        super().__init__(message)


class UserIsAlreadyFamilyMember(FamilyError, ConflictError):
    def __init__(self, message="The user is already a family member"):
        super().__init__(message)


class UserCannotLeaveFamily(FamilyError):
    def __init__(self, message="User cannot leave the family."):
        super().__init__(message)
