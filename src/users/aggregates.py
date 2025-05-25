from pydantic import BaseModel

from users.schemas import UserResponseSchema
from wallets.schemas import WalletBalanceSchema


class MeProfileSchema(BaseModel):
    user: UserResponseSchema
    is_family_member: bool
    wallet: WalletBalanceSchema | None


class UserProfileSchema(BaseModel):
    user: UserResponseSchema
    chore_completion_count: int | None
    chore_confirmed_count: int = 10  # TODO:
