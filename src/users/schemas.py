from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserResponseSchema(BaseModel):
    id: UUID
    username: str
    name: str | None
    icon: str
    icon_color: str
    icon_bg: str
    experience: int

    model_config = ConfigDict(from_attributes=True)


class UserResponseProfile(UserResponseSchema):
    level: int
    exp_to_next_total: int | None
    progress_percent: int
    total_completed: int
    week_completed: int
    month_completed: int
    is_max_level: bool
    is_family_member: bool
    is_family_admin: bool


class UserUpdateSchema(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=50)
    icon: str | None = Field(default=None, max_length=100)
    icon_color: str | None = Field(default=None, max_length=50)
    icon_bg: str | None = Field(default=None, max_length=200)

    @field_validator("username", "name", "icon", "icon_color", "icon_bg", mode="before")
    @classmethod
    def field_not_none(cls, value, info):
        if value is None:
            raise ValueError(f"{info.field_name} cannot be null")
        return value


class UserFamilyPermissionModelSchema(BaseModel):
    can_invite_users: bool


class UserSettingsResponseSchema(BaseModel):
    app_theme: str
    language: str
    date_of_birth: date


class UserSettingsUpdateSchema(BaseModel):
    app_theme: str | None = Field(default=None, max_length=20)
    language: str | None = Field(default=None, max_length=10)
    date_of_birth: date | None = None
