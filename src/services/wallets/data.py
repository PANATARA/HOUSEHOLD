from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import String, case, cast, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from db.models.chore import Chore, ChoreCompletion
from db.models.product import Product
from db.models.user import User
from db.models.wallet import PeerTransaction, RewardTransaction, Wallet
from schemas.wallets import WalletTransactionSchema, WalletBalanceSchema


@dataclass
class WalletDataService:
    """Return  pydantic models"""

    db_session: AsyncSession

    async def get_user_wallet(self, user_id: UUID) -> WalletBalanceSchema | None:
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

        wallet = WalletBalanceSchema(
            id=rows["wallet_id"],
            balance=rows["wallet_balance"],
        )
        return wallet


@dataclass
class TransactionDataService:
    """Return pydantic models"""

    db_session: AsyncSession

    async def get_union_user_transactions(
        self, user_id: UUID, offset: int, limit: int
    ) -> list[WalletTransactionSchema]:
        u = aliased(User)
        p = aliased(Product)
        cc = aliased(ChoreCompletion)
        c = aliased(Chore)

        peer_transactions_query = (
            select(
                PeerTransaction.id,
                PeerTransaction.detail,
                PeerTransaction.coins,
                cast(PeerTransaction.transaction_type, String),
                case(
                    (PeerTransaction.to_user_id == user_id, "incoming"),
                    (PeerTransaction.from_user_id == user_id, "outgoing"),
                ).label("transaction_direction"),
                PeerTransaction.created_at,
                func.json_build_object(
                    "id",
                    u.id,
                    "username",
                    u.username,
                    "name",
                    u.name,
                    "surname",
                    u.surname,
                ).label("other_user"),
                case(
                    (
                        p.id.isnot(None),
                        func.json_build_object(
                            "id", p.id, 
                            "name", p.name, 
                            "description", p.description,
                            "icon", p.icon, 
                            "price", p.price,
                            "is_active", p.is_active,
                            "created_at", p.created_at
                        ),
                    ),
                    else_=None,
                ).label("product"),
                literal(None).label("chore_completion"),
            )
            .join(
                u,
                (u.id == PeerTransaction.from_user_id)
                & (PeerTransaction.from_user_id != user_id)
                | (u.id == PeerTransaction.to_user_id)
                & (PeerTransaction.to_user_id != user_id),
                isouter=True,
            )
            .join(p, p.id == PeerTransaction.product_id, isouter=True)
            .where(
                (PeerTransaction.to_user_id == user_id)
                | (PeerTransaction.from_user_id == user_id)
            )
        )

        reward_transactions_query = (
            select(
                RewardTransaction.id,
                RewardTransaction.detail,
                RewardTransaction.coins,
                cast(RewardTransaction.transaction_type, String),
                func.text("incoming").label("transaction_direction"),
                RewardTransaction.created_at,
                literal(None).label("product"),
                literal(None).label("other_user"),
                func.json_build_object(
                    "id",
                    RewardTransaction.chore_completion_id,
                    "completed_at",
                    cc.created_at,
                    "chore",
                    func.json_build_object(
                        "id",
                        c.id,
                        "name",
                        c.name,
                        "description",
                        c.description,
                        "icon",
                        c.icon,
                        "valuation",
                        c.valuation,
                    ),
                ).label("chore_completion"),
            )
            .join(cc, RewardTransaction.chore_completion_id == cc.id, isouter=True)
            .join(c, c.id == cc.chore_id, isouter=True)
            .where(RewardTransaction.to_user_id == user_id)
        )

        union_query = peer_transactions_query.union_all(reward_transactions_query)
        final_query = union_query.limit(limit).offset(offset)
        query_result = await self.db_session.execute(final_query)
        raw_data = query_result.mappings().all()

        result = []
        for item in raw_data:
            result.append(WalletTransactionSchema.model_validate(item))

        return result
