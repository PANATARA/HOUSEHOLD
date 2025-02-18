import uuid
from sqlalchemy import Boolean, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    permissions: Mapped["UserFamilyPermissions"] = relationship(
        "UserFamilyPermissions", back_populates="user", uselist=False
    )
    settings: Mapped["UserSettings"] = relationship(
        "UserSettings", back_populates="user", uselist=False
    )


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
    user: Mapped["User"] = relationship("User", back_populates="settings")
    app_theme: Mapped[str]

    def __repr__(self):
        return super().__repr__()


class UserFamilyPermissions(Base, BaseModel):
    __tablename__= "users_family_permissions"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="users.id", 
            ondelete="CASCADE",
        )
    )
    user: Mapped["User"] = relationship("User", back_populates="permissions")
    
    should_confirm_chorelog: Mapped[bool]
    should_confirm_creating_chore: Mapped[bool]
    
    can_create_chore: Mapped[bool]
    can_change_family_name: Mapped[bool]
    can_kick_user: Mapped[bool]
    can_invite_users: Mapped[bool]
    can_promote_user: Mapped[bool]
