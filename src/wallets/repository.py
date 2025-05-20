from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import String, case, cast, exists, func, literal, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from chores.models import Chore
from chores_completions.models import ChoreCompletion
from core.base_dals import BaseDals, BaseUserPkDals, DeleteDALMixin
from core.enums import PeerTransactionENUM, RewardTransactionENUM
from products.models import Product
from users.models import User
from wallets.models import PeerTransaction, RewardTransaction, Wallet
from wallets.schemas import (
    PurchaseTransactionSchema,
    RewardTransactionSchema,
    TransferTransactionSchema,
    UnionTransactionsSchema,
    WalletBalanceSchema,
)


class AsyncWalletDAL(BaseUserPkDals[Wallet], DeleteDALMixin):
    model = Wallet

    async def exist_wallet_user(self, user: UUID) -> bool:
        query = select(exists().where(Wallet.user_id == user))
        result = await self.db_session.execute(query)
        return bool(result.scalar() or False)

    async def get_user_balance(self, user_id: UUID) -> Decimal | None:
        query = select(Wallet.balance).where(Wallet.user_id == user_id)
        result = await self.db_session.execute(query)
        balance = result.scalar()
        return Decimal(balance) if balance is not None else None

    async def add_balance(self, user_id: UUID, amount: Decimal) -> Decimal | None:
        query = (
            update(Wallet)
            .where(Wallet.user_id == user_id)
            .values(balance=Wallet.balance + amount)
            .returning(Wallet.balance)
        )

        result = await self.db_session.execute(query)
        await self.db_session.flush()

        return result.scalar()

    async def delete_wallet_user(self, user: UUID) -> None:
        return


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
            balance=rows["wallet_balance"],
        )
        return wallet


@dataclass
class TransactionDataService:
    """Return pydantic models"""

    db_session: AsyncSession

    async def get_union_user_transactions(
        self, user_id: UUID, offset: int, limit: int
    ) -> list[UnionTransactionsSchema]:
        u = aliased(User)
        p = aliased(Product)
        cc = aliased(ChoreCompletion)
        c = aliased(Chore)

        peer_transactions_query = (
            select(
                PeerTransaction.id,
                PeerTransaction.detail,
                PeerTransaction.coins,
                cast(
                    PeerTransaction.transaction_type, String
                ),  # converting enum to string to correctly combine two queries
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
                            "id",
                            p.id,
                            "name",
                            p.name,
                            "description",
                            p.description,
                            "icon",
                            p.icon,
                            "price",
                            p.price,
                            "is_active",
                            p.is_active,
                            "created_at",
                            p.created_at,
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
                cast(
                    RewardTransaction.transaction_type, String
                ),  # converting enum to string to correctly combine two queries
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
            transaction_type = item["transaction_type"]
            if transaction_type == PeerTransactionENUM.purchase.value:
                result.append(PurchaseTransactionSchema.model_validate(item))
            elif transaction_type == PeerTransactionENUM.transfer.value:
                result.append(TransferTransactionSchema.model_validate(item))
            elif transaction_type == RewardTransactionENUM.reward_for_chore.value:
                result.append(RewardTransactionSchema.model_validate(item))
            else:
                raise ValueError(f"Unknown transaction type: {transaction_type}")

        return UnionTransactionsSchema(transactions=result)


class PeerTransactionDAL(BaseDals[PeerTransaction]):

    model = PeerTransaction


class RewardTransactionDAL(BaseDals[RewardTransaction]):

    model = RewardTransaction
