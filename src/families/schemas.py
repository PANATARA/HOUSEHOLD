from datetime import timedelta
from uuid import UUID

from pydantic import BaseModel

from core.enums import StorageFolderEnum
from core.get_avatars import AvatarService
from users.schemas import UserSummarySchema


class FamilyCreateSchema(BaseModel):
    """Schema for creating a new family"""

    name: str
    icon: str


class FamilyBaseSchema(BaseModel):
    name: str
    icon: str
    avatar_url: str | None = None

    async def set_avatar_url(self) -> None:
        self.avatar_url = await AvatarService(
            self.id, StorageFolderEnum.family_avatars
        ).run_process()


class FamilySummarySchema(FamilyBaseSchema):
    id: UUID


class FamilyDetailSchema(FamilySummarySchema):
    # TODO total_score: int
    # total_completed_chores: int = 0
    # top_member_weekly: TopMemberByChoreCompletion | None = None
    members: list[UserSummarySchema]


class FamilyInviteSchema(BaseModel):
    should_confirm_chore_completion: bool


class FamilyJoinSchema(BaseModel):
    invite_token: str


class InviteTokenSchema(BaseModel):
    invite_token: str
    life_time: timedelta
