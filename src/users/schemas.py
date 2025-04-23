from uuid import UUID

from pydantic import BaseModel

from core.enums import StorageFolderEnum
from core.get_avatars import AvatarService


class UserBaseSchema(BaseModel):
    username: str
    name: str
    surname: str | None


class UserSummarySchema(UserBaseSchema):
    id: UUID
    avatar_url: str | None = None

    async def set_avatar_url(self) -> None:
        self.avatar_url = await AvatarService(self.id, StorageFolderEnum.users_avatars).run_process()


class UserCreateSchema(UserBaseSchema):
    password: str


class UserUpdateSchema(BaseModel):
    username: str | None = None
    name: str | None = None
    surname: str | None = None


class UserFamilyPermissionModelSchema(BaseModel):
    should_confirm_chore_completion: bool


class UserSettingsShowSchema(BaseModel):
    app_theme: str
