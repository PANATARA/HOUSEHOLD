import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.models import BaseIdTimeStampModel
from core.models import Base


class Chore(Base, BaseIdTimeStampModel):
    __tablename__ = "chores"

    name: Mapped[str]
    description: Mapped[str]
    icon: Mapped[str]
    valuation: Mapped[int]
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="family.id", ondelete="CASCADE")
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(column="users.id", ondelete="SET NULL")
    )

    def __repr__(self):
        return super().__repr__()
