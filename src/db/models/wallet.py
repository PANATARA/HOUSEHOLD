import uuid
from sqlalchemy import DECIMAL, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

import enum

from db.models.base_model import BaseModel
from db.models.declarative_base import Base


class Wallet(Base, BaseModel):
    __tablename__ = "user_wallet"

    balance: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2), default=0.00, nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="users.id", 
            ondelete="CASCADE",
        )
    )
    user: Mapped["User"] = relationship("User", back_populates="wallet", uselist=False) # type: ignore
    transactions: Mapped["Transaction"] = relationship("Transaction", back_populates="wallet") # type: ignore


    def __repr__(self):
        return super().__repr__()


class TransactionType(enum.Enum):
    purchase = "purchase"
    income = "income"
    transfer = "transfer"


class Transaction(Base, BaseModel):
    __tablename__ = "wallet_transaction"

    description: Mapped[str]
    transaction_type: Mapped[TransactionType]

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
            column="product.id", 
            ondelete="SET NULL",
        )
    )

    chore_log_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            column="family_chore_log.id", 
            ondelete="SET NULL",
        )
    )
    from_user: Mapped["User"] = relationship("User", back_populates="expenses", uselist=False) # type: ignore
    to_user: Mapped["User"] = relationship("User", back_populates="incoming", uselist=False) # type: ignore
    product: Mapped["Product"] = relationship("Product", back_populates="transaction", uselist=False) # type: ignore
    chore_log: Mapped["ChoreLog"] = relationship("ChoreLog", back_populates="transaction", uselist=False) # type: ignore

    def __repr__(self):
        return super().__repr__()