import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import StatusConfirmENUM
from core.models import Base, BaseIdTimeStampModel


class ChoreCompletion(Base, BaseIdTimeStampModel):
    __tablename__ = "chore_completion"

    chore_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="chores.id", ondelete="RESTRICT")
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="family.id", ondelete="CASCADE")
    )
    completed_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="users.id", ondelete="RESTRICT")
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
