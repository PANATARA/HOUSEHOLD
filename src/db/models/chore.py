import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.constants import StatusConfirmENUM
from db.models.base_model import BaseModel, BaseUserModel
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
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(column="users.id", ondelete="SET NULL")
    )

    def __repr__(self):
        return super().__repr__()


class ChoreCompletion(Base, BaseModel):
    __tablename__ = "chore_completion"

    chore_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="chores.id", ondelete="SET NULL")
    )
    completed_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="users.id", ondelete="SET NULL")
    )
    status = mapped_column(
        Enum(
            StatusConfirmENUM,
            name=StatusConfirmENUM.get_enum_name(),
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
        default=StatusConfirmENUM.awaits.value,
    )
    message: Mapped[str] = mapped_column(String(50))

    def __repr__(self):
        return super().__repr__()


class ChoreConfirmation(Base, BaseUserModel):
    __tablename__ = "chore_confirmation"

    chore_completion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="chore_completion.id", ondelete="CASCADE")
    )
    status = mapped_column(
        Enum(
            StatusConfirmENUM,
            name=StatusConfirmENUM.get_enum_name(),
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
        default=StatusConfirmENUM.awaits.value,
    )
