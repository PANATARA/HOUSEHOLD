from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import case, or_, select
from sqlalchemy.orm import aliased

from core.constants import WalletTransactionENUM
from db.models.chore import Chore, ChoreCompletion
from db.models.user import User
from db.models.wallet import TransactionLog, Wallet
from schemas.chores.chores import NewChoreSummary
from schemas.chores.chores_completions import NewChoreCompletionSummaryLite
from schemas.users import UserResponse
from schemas.wallets import ShowWalletBalance, WalletTransactionLog


@dataclass
class WalletDataService:
    """Return  pydantic models"""

    db_session: AsyncSession

    async def get_user_wallet(self, user_id: UUID) -> ShowWalletBalance:
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

        wallet = ShowWalletBalance(
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
    ) -> list[WalletTransactionLog]:
        wt = aliased(TransactionLog)

        query = (
            select(
                case(
                    (wt.transaction_type == WalletTransactionENUM.purchase.value, case(
                        (wt.from_user_id == user_id, 'purchase'),
                        (wt.to_user_id == user_id, 'selling'),
                    )),
                    (wt.transaction_type == WalletTransactionENUM.income.value, case(
                        (wt.to_user_id == user_id, 'earning'),
                    )),
                    (wt.transaction_type == WalletTransactionENUM.transfer.value, case(
                        (wt.from_user_id == user_id, 'outgoing transfer'),
                        (wt.to_user_id == user_id, 'incoming transfer'),
                    )),
                    else_='unknown'
                ).label("transaction_type"),
                wt.description.label("message"),
                wt.created_at.label("datetime"),
                wt.coins.label("coins"),
                User.id.label("user_id"),
                User.username.label("user_username"),
                User.name.label("user_name"),
                User.surname.label("user_surname"),
                ChoreCompletion.id.label("chore_completion_id"),
                ChoreCompletion.created_at.label("chore_completion_created_at"),
                Chore.id.label("chore_completion_chore_id"),
                Chore.name.label("chore_completion_chore_name"),
                Chore.icon.label("chore_completion_chore_icon"),
                Chore.valuation.label("chore_completion_chore_valuation")
            )
            .outerjoin(
                User, 
                or_(
                    (wt.from_user_id == User.id) & (wt.from_user_id != user_id),
                    (wt.to_user_id == User.id) & (wt.to_user_id != user_id)
                )
            )
            .outerjoin(
                ChoreCompletion, wt.chore_completion_id==ChoreCompletion.id
            )
            .outerjoin(
                Chore, ChoreCompletion.chore_id==Chore.id
            )
            .where((wt.from_user_id == user_id) | (wt.to_user_id == user_id))
            .order_by(wt.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()

        return [
            WalletTransactionLog(
                description = item["message"],
                transaction_type = item["transaction_type"],
                coins = item["coins"],
                user = UserResponse(
                    id=item["user_id"],
                    username=item["user_username"],
                    name=item["user_name"],
                    surname=item["user_surname"],
                ) if item["user_id"] else None,
                chore_completion = NewChoreCompletionSummaryLite(
                    id=item["chore_completion_id"],
                    chore=NewChoreSummary(
                        id = item["chore_completion_chore_id"],
                        name = item["chore_completion_chore_name"],
                        icon = item["chore_completion_chore_icon"],
                        valuation = item["chore_completion_chore_valuation"],
                    ),
                    completed_at=item["chore_completion_created_at"]
                ) if item["chore_completion_id"] else None,
            )
            for item in raw_data
        ]
