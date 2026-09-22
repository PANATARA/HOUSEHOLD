from typing import TYPE_CHECKING
from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import Base, BaseUserModel

if TYPE_CHECKING:
    from users.models import User


class UserDevice(Base, BaseUserModel):
    __tablename__ = "user_devices"
    __table_args__ = (
        Index("ix_user_devices_user_id", "user_id"),
    )

    token: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), default="android", nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(100), default=None, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="devices")

    def __repr__(self) -> str:
        return f"<UserDevice(id={self.id}, user_id={self.user_id}, device_type={self.device_type})>"
