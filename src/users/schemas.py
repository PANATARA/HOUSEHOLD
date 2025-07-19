from datetime import date
from uuid import UUID

from pydantic import BaseModel, field_validator

from core.enums import StorageFolderEnum
from core.get_avatars import AvatarService


class UserResponseSchema(BaseModel):
    id: UUID
    username: str
    name: str | None
    surname: str | None
    avatar_url: str | None = None

    async def set_avatar_url(self) -> None:
        self.avatar_url = await AvatarService(
            self.id, StorageFolderEnum.users_avatars
        ).run_process()


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
