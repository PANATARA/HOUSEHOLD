from uuid import UUID
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.dals.wallets import AsyncWalletDAL
from db.models.wallet import Wallet
from schemas.wallets import ShowWallet


@dataclass
class WalletDataService:
    """Return  pydantic models"""

    db_session: AsyncSession

    async def get_user_wallet(self, user_id: UUID) -> ShowWallet:
        """Returns a pydantic model of the user wallet"""
        result = await self.db_session.execute(
            select(
                Wallet.id.label("wallet_id"),
                Wallet.balance.label("wallet_balance"),
            )
            .where(Wallet.user_id == user_id)
        )

        rows = result.mappings().first()

        if not rows:
            return None

        wallet = ShowWallet(
            id = rows["wallet_id"],
            balance=rows["wallet_balance"],
        )
        return wallet 