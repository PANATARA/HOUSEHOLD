import uuid

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.models import BaseUserModel
from core.enums import StatusConfirmENUM
from core.models import Base


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
