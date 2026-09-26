import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index
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
        ),
        index=True,
    )
    total_completed: Mapped[int] = mapped_column(server_default="0", nullable=False)
    experience: Mapped[int] = mapped_column(default=0)

    def __repr__(self):
        return super().__repr__()


class Event(Base, BaseIdTimeStampModel):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_family_id_date", "family_id", "date"),)

    name: Mapped[str]
    description: Mapped[str | None]
    date: Mapped[datetime]
    created_at: Mapped[datetime]
    icon: Mapped[str] = mapped_column(server_default="material-symbols:home-rounded")
    icon_color: Mapped[str] = mapped_column(server_default="#ffffff")
    icon_bg: Mapped[str] = mapped_column(
        server_default="linear-gradient(135deg, #e8a87c 0%, #c17a45 100%)"
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="family.id", ondelete="CASCADE")
    )

    def __repr__(self):
        return super().__repr__()
