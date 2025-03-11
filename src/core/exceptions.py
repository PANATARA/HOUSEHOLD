from fastapi import HTTPException
from starlette import status


class UserError(Exception):
    """Base exception for all errors related to family actions."""
    pass


class FamilyError(Exception):
    """Base exception for all errors related to family actions."""
    pass


class WalletError(Exception):
    """Base exception for all errors related to wallet actions."""
    pass


class ChoreError(Exception):
    """Base exception for all errors related to chores actions."""
    pass


class ChoreCompletionError(Exception):
    """Base exception for all errors related to chore completion actions."""
    pass


class ChoreConfirmationError(Exception):
    """Base exception for all errors related to chore completion actions."""
    pass


class ProductError(Exception):
    """Base exception for all errors related to product actions."""
    pass


class UserCannotLeaveFamily(FamilyError):
    def __init__(self, message="User cannot leave the family."):
        super().__init__(message)


class UserIsAlreadyFamilyMember(FamilyError):
    def __init__(self, message="The user is already a family member"):
        super().__init__(message)


class NoSuchUserFoundInTheFamily(FamilyError):
    def __init__(self, message="No such user found in the family."):
        super().__init__(message)


class ChoreNotFoundError(ChoreError):
    def __init__(self, message="The specified chore was not found."):
            super().__init__(message)


class ChoreCompletionCanNotBeChanged(ChoreError):
    def __init__(self, message="The specified chore completion can't be cahnged"):
            super().__init__(message)


class NotEnoughCoins(WalletError):
    def __init__(self, message="User does not have enough coins for the transaction."):
        super().__init__(message)


class ProductNotFoundError(ProductError):
    def __init__(self, message="The specified product was not found."):
        super().__init__(message)


class DebugError(Exception):
    def __init__(self, message="Debugging error occurred."):
        self.message = message
        super().__init__(self.message)


permission_denided = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Forbidden",
)

user_not_found = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Such user not found",
)

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
)
