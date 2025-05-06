import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import BaseIdTimeStampModel, OneToOneUserModel
from core.models import Base


class User(Base, BaseIdTimeStampModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    surname: Mapped[str | None] = mapped_column(String(50))
    family_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(column="family.id", ondelete="SET NULL", use_alter=True)
    )

    password: Mapped[str]
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


class UserSettings(Base, OneToOneUserModel):
    __tablename__ = "users_settings"

    user: Mapped["User"] = relationship("User", back_populates="settings")
    app_theme: Mapped[str] = mapped_column(String, default="Dark")
    language: Mapped[str] = mapped_column(String, default="ru")
    date_of_birth: Mapped[date] = mapped_column(Date, default=date(2001, 1, 1))

    def __repr__(self):
        return super().__repr__()


class UserFamilyPermissions(Base, OneToOneUserModel):
    __tablename__ = "users_family_permissions"

    should_confirm_chore_completion: Mapped[bool]
    can_invite_users: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship("User", back_populates="permissions")
