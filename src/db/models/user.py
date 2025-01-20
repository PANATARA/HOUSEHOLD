import uuid
from sqlalchemy import Boolean, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base_model import BaseModel
from db.models.declarative_base import Base


class User(Base, BaseModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    surname: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    hashed_password: Mapped[str]

    family_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            column="family.id", 
            ondelete="SET NULL",
        )
    )
    family: Mapped["Family"] = relationship("Family", back_populates="users", uselist=False) # type: ignore
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="user", uselist=False) # type: ignore
    chore_logs: Mapped["ChoreLog"] = relationship("ChoreLog", back_populates="completed_by") # type: ignore
    expenses: Mapped["Transaction"] = relationship("Transaction", back_populates="from_user", foreign_keys="Transaction.from_user_id") # type: ignore
    incoming: Mapped["Transaction"] = relationship("Transaction", back_populates="to_user", foreign_keys="Transaction.to_user_id") # type: ignore
    seller: Mapped["Product"] = relationship("Product", back_populates="seller", foreign_keys="Product.seller_id") # type: ignore
    buyer: Mapped["Product"] = relationship("Product", back_populates="buyer", foreign_keys="Product.buyer_id") # type: ignore

    def __repr__(self):
        return super().__repr__()