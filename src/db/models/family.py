import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, SmallInteger, String

from db.models.base_model import BaseModel
from db.models.declarative_base import Base


class Family(Base, BaseModel):
    __tablename__ = "family"

    name: Mapped[str]

    def __repr__(self):
        return super().__repr__()


class FamilySettings(Base, BaseModel):
    __tablename__ = "family_settings"

    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="family.id",
            ondelete="CASCADE",
        )
    )
    confirm_by_all_admins: Mapped[bool] = mapped_column(Boolean, default=False)
    icon: Mapped[str]  = mapped_column(String, default="DefaultIcon")

    def __repr__(self):
        return super().__repr__()
