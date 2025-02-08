import uuid
from enum import Enum
from sqlalchemy import CheckConstraint, ForeignKey, String, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base_model import BaseModel
from db.models.declarative_base import Base


class Chore(Base, BaseModel):
    __tablename__ = "chores"

    name: Mapped[str]
    description: Mapped[str]
    icon: Mapped[str]
    valuation: Mapped[int]
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="family.id", ondelete="CASCADE")
    )

    def __repr__(self):
        return super().__repr__()


class ChoreLog(Base, BaseModel):
    __tablename__ = "chores_logs"

    chore_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(column="chores.id", ondelete="SET NULL")
    )
    completed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(column="users.id", ondelete="SET NULL")
    )
    status: Mapped[int] = mapped_column(
        SmallInteger,
        CheckConstraint("status BETWEEN 0 AND 2"),
        nullable=False,
        default=0,
    )
    message: Mapped[str] = mapped_column(String(50))

    def __repr__(self):
        return super().__repr__()


class ChoreLogConfirm(Base, BaseModel):
    __tablename__ = "chores_logs_confirms"

    chore_log_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="chores_logs.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="users.id", ondelete="CASCADE")
    )
    status: Mapped[int] = mapped_column(
        SmallInteger,
        CheckConstraint("status BETWEEN 0 AND 2"),
        nullable=False,
        default=0,
    )
