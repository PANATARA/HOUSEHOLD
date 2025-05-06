import uuid

from pydantic import BaseModel
from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.models import BaseIdTimeStampModel
from core.enums import StatusConfirmENUM
from core.models import Base


class ChoreCompletion(Base, BaseIdTimeStampModel):
    __tablename__ = "chore_completion"

    chore_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(column="chores.id", ondelete="SET NULL")
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="family.id", ondelete="CASCADE")
    )
    completed_by_id: Mapped[uuid.UUID | None] = mapped_column(
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


class ChoreCompletionModel(BaseModel):
    family_id: uuid.UUID
    message: str
    completed_by_id: uuid.UUID
    chore_id: uuid.UUID
    status: StatusConfirmENUM
