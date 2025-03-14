import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base_model import BaseModel, BaseUserModel
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

    hashed_password: Mapped[str]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    permissions: Mapped["UserFamilyPermissions"] = relationship(
        "UserFamilyPermissions", back_populates="user", uselist=False
    )
    settings: Mapped["UserSettings"] = relationship(
        "UserSettings", back_populates="user", uselist=False
    )

    def __repr__(self):
        return super().__repr__()


class UserSettings(Base, BaseUserModel):
    __tablename__ = "users_settings"

    user: Mapped["User"] = relationship("User", back_populates="settings")
    app_theme: Mapped[str]

    def __repr__(self):
        return super().__repr__()


class UserFamilyPermissions(Base, BaseUserModel):
    __tablename__ = "users_family_permissions"

    should_confirm_chore_completion: Mapped[bool]
    can_invite_users: Mapped[bool] = True

    user: Mapped["User"] = relationship("User", back_populates="permissions")
