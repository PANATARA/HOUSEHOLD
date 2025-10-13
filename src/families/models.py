import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.models import Base, BaseIdTimeStampModel


class Family(Base, BaseIdTimeStampModel):
    __tablename__ = "family"

    name: Mapped[str]
    icon: Mapped[str] = mapped_column(String, default="DefaultIcon")
    family_admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="users.id",
            ondelete="SET NULL",
        )
    )
    avatar_version: Mapped[int | None] = mapped_column(default=None)
    avatar_extension: Mapped[str | None] = mapped_column(default=None)

    def __repr__(self):
        return super().__repr__()
