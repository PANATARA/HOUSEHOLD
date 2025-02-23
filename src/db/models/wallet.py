import uuid
import enum
from sqlalchemy import DECIMAL, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.constants import WalletTransactionENUM
from db.models.base_model import BaseModel
from db.models.declarative_base import Base



class Wallet(Base, BaseModel):
    __tablename__ = "wallets"

    balance: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2), default=0.00, nullable=False)

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
        Enum(name=WalletTransactionENUM.get_enum_name(), create_type=False, native_enum=False),
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