from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, field_validator

from config import LETTER_MATCH_PATTERN, PASSWORD_PATTERN
from core.enums import StorageFolderEnum
from core.get_avatars import AvatarService


class UserSummarySchema(BaseModel):
    id: UUID
    username: str
    name: str
    surname: str | None
    avatar_url: str | None = None

    async def set_avatar_url(self) -> None:
        self.avatar_url = await AvatarService(self.id, StorageFolderEnum.users_avatars).run_process()


class UserCreateSchema(BaseModel):
    username: str
    name: str
    surname: str
    password: str

    @field_validator("name")
    def validate_name(cls, value):
        if not LETTER_MATCH_PATTERN.match(value):
            raise HTTPException(
                status_code=422, detail="Name should contains only letters"
            )
        return value

    @field_validator("surname")
    def validate_surname(cls, value):
        if not LETTER_MATCH_PATTERN.match(value):
            raise HTTPException(
                status_code=422, detail="Surname should contains only letters"
            )
        return value

    @field_validator("password")
    def validate_password(cls, value):
        if not PASSWORD_PATTERN.match(value):
            raise HTTPException(status_code=422, detail="Password validation Error")
        return value


class UserUpdateSchema(BaseModel):
    username: str | None = None
    name: str | None = None
    surname: str | None = None

    @field_validator("name")
    def validate_name(cls, value):
        if not LETTER_MATCH_PATTERN.match(value):
            raise HTTPException(
                status_code=422, detail="Name should contains only letters"
            )
        return value

    @field_validator("surname")
    def validate_surname(cls, value):
        if not LETTER_MATCH_PATTERN.match(value):
            raise HTTPException(
                status_code=422, detail="Surname should contains only letters"
            )
        return value


class UserFamilyPermissionModelSchema(BaseModel):
    should_confirm_chore_completion: bool


class UserSettingsShowSchema(BaseModel):
    user_id: UUID
    app_theme: str
