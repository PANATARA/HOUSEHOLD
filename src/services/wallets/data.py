from uuid import UUID
from dataclasses import dataclass
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.wallet import Wallet
from schemas.wallets import CoinTransactionLog, ShowWallet


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
            ).where(Wallet.user_id == user_id)
        )

        rows = result.mappings().first()

        if not rows:
            return None

        wallet = ShowWallet(
            id=rows["wallet_id"],
            balance=rows["wallet_balance"],
        )
        return wallet


@dataclass
class TransactionDataService:
    """Return pydantic models"""

    db_session: AsyncSession

    async def get_user_transactions(
        self, user_id: UUID, offset: int, limit: int
    ) -> list[CoinTransactionLog]:
        query = text(
            """ 
        SELECT
            CASE 
                WHEN wt.transaction_type = 0 AND wt.from_user_id = :user_id THEN 'purchase'
                WHEN wt.transaction_type = 0 AND wt.to_user_id = :user_id THEN 'selling'
                WHEN wt.transaction_type = 1 AND wt.to_user_id = :user_id THEN 'earning'
                WHEN wt.transaction_type = 2 AND wt.from_user_id = :user_id THEN 'outgoing transfer'
                WHEN wt.transaction_type = 2 AND wt.to_user_id = :user_id THEN 'incoming transfer'
                ELSE 'unknown'
            END AS "transaction_type",
            wt.description AS "message",
            CASE 
                WHEN wt.from_user_id = :user_id THEN wt.to_user_id
                ELSE wt.from_user_id
            END AS "transaction_with_user_id",
            u.username AS "other_user_username",
            u."name" AS "other_user_name",
            u.surname AS "other_user_surname",
            wt.created_at AS "datetime",
            wt.coins AS "coins"
        FROM wallets_transactions wt
        JOIN users u ON 
            (wt.from_user_id = u.id AND wt.from_user_id <> :user_id) 
            OR 
            (wt.to_user_id = u.id AND wt.to_user_id <> :user_id)
        WHERE 
            wt.from_user_id = :user_id 
            OR wt.to_user_id = :user_id
        ORDER BY wt.created_at DESC
        LIMIT :limit OFFSET :offset;
        """
        )
        result = await self.db_session.execute(
            query, {"user_id": user_id, "limit": limit, "offset": offset}
        )
        raw_data = result.mappings().all()

        return [CoinTransactionLog.model_validate(item) for item in raw_data]
