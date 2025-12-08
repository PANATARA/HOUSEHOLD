from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class UserResponseSchema(BaseModel):
    id: UUID
    username: str
    name: str | None
    surname: str | None
    avatar_version: int | None

    model_config = ConfigDict(from_attributes=True)


class UserUpdateSchema(BaseModel):
    username: str | None = None
    name: str | None = None
    surname: str | None = None

    @field_validator("username", "name", "surname", mode="before")
    @classmethod
    def field_not_none(cls, value, info):
        if value is None:
            raise ValueError(f"{info.field_name} cannot be null")
        return value


class UserFamilyPermissionModelSchema(BaseModel):
    should_confirm_chore_completion: bool


class UserSettingsResponseSchema(BaseModel):
    app_theme: str
    language: str
    date_of_birth: date


class UserSettingsUpdateSchema(BaseModel):
    app_theme: str | None = None
    language: str | None = None
    date_of_birth: date | None = None
