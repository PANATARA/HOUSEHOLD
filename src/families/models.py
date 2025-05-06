import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.models import BaseIdTimeStampModel
from core.models import Base


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

    def __repr__(self):
        return super().__repr__()
