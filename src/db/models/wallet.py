import uuid
from sqlalchemy import DECIMAL, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.constants import (
    PeerTransactionENUM,
    RewardTransactionENUM,
    WalletTransactionENUM,
)
from db.models.base_model import BaseModel
from db.models.declarative_base import Base


class Wallet(Base, BaseModel):
    __tablename__ = "wallets"

    balance: Mapped[DECIMAL] = mapped_column(
        DECIMAL(10, 2), default=0.00, nullable=False
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="users.id",
            ondelete="CASCADE",
        )
    )

    def __repr__(self):
        return super().__repr__()


class TransactionLog(Base, BaseModel):
    __tablename__ = "wallets_transactions"

    description: Mapped[str]
    transaction_type = mapped_column(
        Enum(
            WalletTransactionENUM,
            name=WalletTransactionENUM.get_enum_name(),
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
    )
    coins: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2), nullable=False)

    from_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            column="users.id",
            ondelete="SET NULL",
        )
    )
    to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            column="users.id",
            ondelete="SET NULL",
        )
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            column="products.id",
            ondelete="SET NULL",
        )
    )

    chore_completion_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            column="chore_completion.id",
            ondelete="SET NULL",
        )
    )

    def __repr__(self):
        return super().__repr__()


class BaseTransaction(Base, BaseModel):
    __abstract__ = True

    detail: Mapped[str]
    coins: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2), nullable=False)
    to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


class PeerTransaction(BaseTransaction):
    __tablename__ = "peer_transactions"

    transaction_type: Mapped[PeerTransactionENUM] = mapped_column(
        Enum(
            PeerTransactionENUM,
            name=PeerTransactionENUM.get_enum_name(),
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
    )
    from_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True
    )


class RewardTransaction(BaseTransaction):
    __tablename__ = "reward_transactions"

    transaction_type: Mapped[RewardTransactionENUM] = mapped_column(
        Enum(
            RewardTransactionENUM,
            name=RewardTransactionENUM.get_enum_name(),
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
    )
    chore_completion_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chore_completion.id", ondelete="SET NULL"), index=True
    )
