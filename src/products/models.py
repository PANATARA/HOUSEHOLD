import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.models import Base, BaseIdTimeStampModel


class Product(Base, BaseIdTimeStampModel):
    __tablename__ = "products"

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
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="users.id",
            ondelete="RESTRICT",
        )
    )
    avatar_version: Mapped[int | None] = mapped_column(default=None)
    avatar_extension: Mapped[str | None] = mapped_column(default=None)

    def __repr__(self):
        return super().__repr__()


# delete in the future
class ProductBuyer(Base, BaseIdTimeStampModel):
    __tablename__ = "product_buyers"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
