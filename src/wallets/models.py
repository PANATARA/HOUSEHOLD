import uuid

from sqlalchemy import Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import (
    PeerTransactionENUM,
    RewardTransactionENUM,
)
from core.models import Base, BaseIdTimeStampModel, OneToOneUserModel


class Wallet(Base, OneToOneUserModel):
    __tablename__ = "wallets"
    """
    User wallet model
    """

    balance: Mapped[int] = mapped_column(default=0, nullable=False)

    def __repr__(self):
        return super().__repr__()


class BaseTransaction(Base, BaseIdTimeStampModel):
    """
    Basic model of financial transactions
    """

    __abstract__ = True

    detail: Mapped[str]
    coins: Mapped[int] = mapped_column(nullable=False)
    to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


class PeerTransaction(BaseTransaction):
    """
    A model for storing financial transactions between users only
    """

    __tablename__ = "peer_transactions"
    __table_args__ = (
        Index("ix_peer_transactions_to_user_created", "to_user_id", "created_at"),
        Index("ix_peer_transactions_from_user_created", "from_user_id", "created_at"),
    )

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
    """
    A model for storing financial transactions between an application and a user
    """

    __tablename__ = "reward_transactions"
    __table_args__ = (
        Index("ix_reward_transactions_to_user_created", "to_user_id", "created_at"),
    )

    transaction_type: Mapped[RewardTransactionENUM] = mapped_column(
        Enum(
            RewardTransactionENUM,
            name=RewardTransactionENUM.get_enum_name(),
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
    )
    planned_chore_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("planned_chore.id", ondelete="SET NULL"), index=True
    )
