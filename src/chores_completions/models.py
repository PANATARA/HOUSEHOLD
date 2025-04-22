import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.base_model import BaseModel
from core.enums import StatusConfirmENUM
from core.models import Base


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
    synced_to_ch: Mapped[bool] = mapped_column(default=False)

    def __repr__(self):
        return super().__repr__()