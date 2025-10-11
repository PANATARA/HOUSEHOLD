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
    avatar_url: str | None = None


class FamilyDetailSchema(BaseModel):
    family: FamilyResponseSchema
    members: list[UserResponseSchema]


class FamilyInviteSchema(BaseModel):
    should_confirm_chore_completion: bool


class FamilyJoinSchema(BaseModel):
    invite_token: str


class InviteTokenSchema(BaseModel):
    invite_token: str
    life_time: timedelta
