import uuid

from sqlalchemy import DECIMAL, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.models import BaseIdTimeStampModel, OneToOneUserModel
from core.enums import (
    PeerTransactionENUM,
    RewardTransactionENUM,
)
from core.models import Base


class Wallet(Base, OneToOneUserModel):
    __tablename__ = "wallets"
    """
    User wallet model
    """

    balance: Mapped[DECIMAL] = mapped_column(
        DECIMAL(10, 2), default=0.00, nullable=False
    )

    def __repr__(self):
        return super().__repr__()


class BaseTransaction(Base, BaseIdTimeStampModel):
    """
    Basic model of financial transactions
    """

    __abstract__ = True

    detail: Mapped[str]
    coins: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2), nullable=False)
    to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


class PeerTransaction(BaseTransaction):
    """
    A model for storing financial transactions between users only
    """

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
    """
    A model for storing financial transactions between an application and a user
    """

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
