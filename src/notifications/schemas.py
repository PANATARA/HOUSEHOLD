from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field


class DeviceRegisterSchema(BaseModel):
    token: str = Field(..., min_length=10, max_length=512, description="FCM device registration token")
    device_type: str = Field(default="android", max_length=50, description="Device platform, currently 'android'")
    device_name: str | None = Field(default=None, max_length=100, description="Optional human-readable device name")


class DeviceResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    token: str
    device_type: str
    device_name: str | None
    created_at: datetime
    updated_at: datetime


class NotificationSendTestSchema(BaseModel):
    title: str = Field(default="Тестовое уведомление", max_length=150)
    body: str = Field(default="Тестовое уведомление из приложения Household", max_length=500)
    data: dict[str, str] | None = Field(default=None)
