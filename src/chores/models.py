import uuid

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import Base, BaseIdTimeStampModel


class Chore(Base, BaseIdTimeStampModel):
    __tablename__ = "chores"
    __table_args__ = (
        Index("ix_chores_family_id_is_active", "family_id", "is_active"),
    )

    name: Mapped[str]
    description: Mapped[str | None]
    icon: Mapped[str] = mapped_column(server_default="material-symbols:mop")
    icon_color: Mapped[str] = mapped_column(server_default="#ffffff")
    icon_bg: Mapped[str] = mapped_column(
        server_default="linear-gradient(135deg, #8a7f6e 0%, #6b5f50 100%)"
    )
    valuation: Mapped[int]
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="family.id", ondelete="CASCADE")
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(column="users.id", ondelete="SET NULL")
    )
    default_chore_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("default_chore.id", ondelete="SET NULL"),
        index=True,
    )

    def __repr__(self):
        return super().__repr__()


class DefaultChore(Base, BaseIdTimeStampModel):
    __tablename__ = "default_chore"
    __table_args__ = (
        Index("ix_default_chore_is_active_order", "is_active", "order"),
    )

    icon: Mapped[str] = mapped_column(server_default="material-symbols:mop")
    icon_color: Mapped[str] = mapped_column(server_default="#ffffff")
    icon_bg: Mapped[str] = mapped_column(
        server_default="linear-gradient(135deg, #8a7f6e 0%, #6b5f50 100%)"
    )
    valuation: Mapped[int]
    order: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)

    translations: Mapped[list["DefaultChoreTranslation"]] = relationship(
        back_populates="default_chore"
    )


class DefaultChoreTranslation(Base, BaseIdTimeStampModel):
    __tablename__ = "default_chore_translation"
    __table_args__ = (
        Index("ix_default_chore_trans_chore_id_lang", "default_chore_id", "language"),
    )

    default_chore_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("default_chore.id", ondelete="CASCADE")
    )
    language: Mapped[str]
    name: Mapped[str]
    description: Mapped[str | None]

    default_chore: Mapped["DefaultChore"] = relationship(back_populates="translations")
