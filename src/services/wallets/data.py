from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from db.dals.wallets import AsyncWalletDAL
from schemas.wallets import ShowWallet


@dataclass
class WalletDataService:
    """Return  pydantic models"""

    db_session: AsyncSession

    async def get_user_wallet(self, user_id: UUID) -> ShowWallet:
        """Returns a pydantic model of the user wallet"""
        wallet_dal = AsyncWalletDAL(self.db_session)
        rows = await wallet_dal.get_wallet_user(user_id)
        
        if rows is None:
            return None

        wallet = ShowWallet(
            id = rows["wallet_id"],
            balance=rows["wallet_balance"],
        )
        return wallet 