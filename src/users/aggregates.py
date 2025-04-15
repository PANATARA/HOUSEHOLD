from pydantic import BaseModel

from users.schemas import UserSummarySchema
from wallets.schemas import WalletBalanceSchema


class UserProfileSchema(BaseModel):
    user: UserSummarySchema
    wallet: WalletBalanceSchema | None