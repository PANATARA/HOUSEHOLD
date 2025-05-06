import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class BaseIdTimeStampModel:
    """FIELDS:
    - primary_key : UUID
    - created_at : datetime
    - updated_at : datetime

    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())"),
        onupdate=text("TIMEZONE('utc', now())"),
    )


class BaseUserModel(BaseIdTimeStampModel):
    __abstract__ = True

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="users.id",
            ondelete="CASCADE",
        )
    )


class OneToOneUserModel(BaseUserModel):
    __abstract__ = True

    @declared_attr
    def user_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
