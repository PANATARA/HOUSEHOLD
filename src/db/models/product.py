import uuid
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base_model import BaseModel
from db.models.declarative_base import Base


class Product(Base, BaseModel):
    __tablename__ = "product"

    name: Mapped[str]
    description: Mapped[str]
    icon: Mapped[str]
    price: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)

    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="family.id", 
            ondelete="CASCADE",
        )
    )
    seller_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            column="users.id", 
            ondelete="SET NULL",
        )
    )
    buyer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            column="users.id", 
            ondelete="SET NULL",
        )
    )

    family: Mapped["Family"] = relationship("Family", back_populates="products") # type: ignore
    seller: Mapped["User"] = relationship("User", back_populates="seller") # type: ignore
    buyer: Mapped["User"] = relationship("User", back_populates="buyer") # type: ignore



    def __repr__(self):
        return super().__repr__()
    
