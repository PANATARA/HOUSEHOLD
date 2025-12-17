from datetime import timedelta
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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
    experience: int

    model_config = ConfigDict(from_attributes=True)


class FamilyMembersSchema(BaseModel):
    members: list[UserResponseSchema]


class FamilyMemberStatsSchema(BaseModel):
    member: UserResponseSchema | None
    chore_completion_count: int | None


class FamilyInviteSchema(BaseModel):
    should_confirm_chore_completion: bool


class FamilyJoinSchema(BaseModel):
    invite_token: str


class InviteTokenSchema(BaseModel):
    invite_token: str
    life_time: timedelta
