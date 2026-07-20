import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.models import Base, BaseIdTimeStampModel


class Family(Base, BaseIdTimeStampModel):
    __tablename__ = "family"

    name: Mapped[str]
    icon: Mapped[str] = mapped_column(server_default="material-symbols:home-rounded")
    icon_color: Mapped[str] = mapped_column(server_default="#ffffff")
    icon_bg: Mapped[str] = mapped_column(
        server_default="linear-gradient(135deg, #e8a87c 0%, #c17a45 100%)"
    )
    family_admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="users.id",
            ondelete="SET NULL",
        )
    )
    avatar_version: Mapped[int | None] = mapped_column(default=None)
    avatar_extension: Mapped[str | None] = mapped_column(default=None)
    total_completed: Mapped[int] = mapped_column(server_default="0", nullable=False)
    experience: Mapped[int] = mapped_column(default=0)

    def __repr__(self):
        return super().__repr__()
