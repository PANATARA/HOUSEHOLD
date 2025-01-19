from sqlalchemy.orm import Mapped, relationship

from db.models.base_model import BaseModel
from db.models.declarative_base import Base


class Family(Base, BaseModel):
    __tablename__ = "family"

    name: Mapped[str]
    users: Mapped[list["User"]] = relationship("User", back_populates="family") # type: ignore
    products: Mapped["Product"] = relationship("Product", back_populates="family") # type: ignore

    def __repr__(self):
        return super().__repr__()

