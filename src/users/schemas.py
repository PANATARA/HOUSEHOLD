from datetime import date
from uuid import UUID

from pydantic import BaseModel

from core.enums import StorageFolderEnum
from core.get_avatars import AvatarService
from core.hashing import Hasher


class UserCreateSchema(BaseModel):
    username: str
    name: str
    surname: str | None
    password: str

    def hash_password(self):
        self.password = Hasher.get_password_hash(self.password)


class UserResponseSchema(BaseModel):
    id: UUID
    username: str
    name: str
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


class UserFamilyPermissionModelSchema(BaseModel):
    should_confirm_chore_completion: bool


class UserSettingsResponseSchema(BaseModel):
    app_theme: str
    language: str
    date_of_birth: date


class UserSettingsCreateSchema(BaseModel):
    user_id: UUID
    app_theme: str
    language: str
    date_of_birth: date
