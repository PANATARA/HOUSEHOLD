from pydantic import BaseModel

from users.schemas import UserSummarySchema
from wallets.schemas import WalletBalanceSchema


class UserProfileSchema(BaseModel):
    user: UserSummarySchema
    is_family_member: bool
    wallet: WalletBalanceSchema | None