from datetime import timedelta
from uuid import UUID

from pydantic import BaseModel

from core.constants import StorageFolderEnum
from core.get_avatars import AvatarService
from users.schemas import UserSummarySchema

class FamilyBaseSchema(BaseModel):
    name: str
    icon: str
    avatar_url: str | None = None

    async def set_avatar_url(self) -> None:
        self.avatar_url = await AvatarService(self.id, StorageFolderEnum.family_avatars).run_process()

class FamilyCreateSchema(FamilyBaseSchema):
    """Schema for creating a new family"""


class FamilySchema(FamilyBaseSchema):
    id: UUID


class FamilyWithMembersSchema(FamilySchema):
    members: list[UserSummarySchema]

    class Config:
        orm_mode = True
        from_attributes = True


class UserInviteParametrSchema(BaseModel):
    should_confirm_chore_completion: bool


class InviteTokenSchema(BaseModel):
    invite_token: str
    life_time: timedelta


class JoinFamilySchema(BaseModel):
    invite_token: str
