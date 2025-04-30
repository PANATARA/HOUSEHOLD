from pydantic import BaseModel

from users.schemas import UserSummarySchema
from wallets.schemas import WalletBalanceSchema


class MeProfileSchema(BaseModel):
    user: UserSummarySchema
    is_family_member: bool
    wallet: WalletBalanceSchema | None

class UserProfileSchema(BaseModel):
    user: UserSummarySchema
    chore_copletion_count: int = 10 # TODO:
    chore_confirmed_count: int = 10 # TODO:
