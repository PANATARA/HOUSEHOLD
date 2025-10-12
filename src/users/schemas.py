from datetime import date
from uuid import UUID

from pydantic import BaseModel, computed_field, field_validator

from config import BASE_URL


class UserResponseSchema(BaseModel):
    id: UUID
    username: str
    name: str | None
    surname: str | None

    @computed_field
    @property
    def avatar_url(self) -> str:
        return f"{BASE_URL}/api/users/{self.id}/avatar"


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
