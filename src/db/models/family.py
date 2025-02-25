import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, ForeignKey, String

from db.models.base_model import BaseModel
from db.models.declarative_base import Base


class Family(Base, BaseModel):
    __tablename__ = "family"

    name: Mapped[str]
    icon: Mapped[str]  = mapped_column(String, default="DefaultIcon")
    family_admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="users.id", 
            ondelete="SET NULL",
        )
    )

    def __repr__(self):
        return super().__repr__()
