import uuid
from sqlalchemy import Boolean, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base_model import BaseModel
from db.models.declarative_base import Base


class User(Base, BaseModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    surname: Mapped[str | None] = mapped_column(String(50))
    family_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            column="family.id", 
            ondelete="SET NULL",
        )
    )
    is_family_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    hashed_password: Mapped[str]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)


    def __repr__(self):
        return super().__repr__()


class UserSettings(Base, BaseModel):
    __tablename__ = "users_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="users.id", 
            ondelete="CASCADE",
        )
    )
    app_theme: Mapped[str]

    def __repr__(self):
        return super().__repr__()