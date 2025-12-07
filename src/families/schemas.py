from datetime import timedelta
from uuid import UUID

from pydantic import BaseModel

from users.schemas import UserResponseSchema


class FamilyCreateSchema(BaseModel):
    """Schema for creating a new family"""

    name: str
    icon: str


class FamilyResponseSchema(BaseModel):
    id: UUID
    name: str
    icon: str
    avatar_version: int | None

    class Config:
        from_attributes = True


class FamilyStatisticsSchema(BaseModel):
    weekly_completed_chores: int
    monthly_completed_chores: int


class FamilyDetailSchema(BaseModel):
    family: FamilyResponseSchema
    statistics: FamilyStatisticsSchema


class FamilyMembersSchema(BaseModel):
    members: list[UserResponseSchema]


class FamilyMemberStatsSchema(BaseModel):
    member: UserResponseSchema
    chore_completion_count: int


class FamilyInviteSchema(BaseModel):
    should_confirm_chore_completion: bool


class FamilyJoinSchema(BaseModel):
    invite_token: str


class InviteTokenSchema(BaseModel):
    invite_token: str
    life_time: timedelta
