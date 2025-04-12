from datetime import timedelta
from uuid import UUID

from pydantic import BaseModel

from users.schemas import UserSummarySchema

class FamilyBaseSchema(BaseModel):
    name: str
    icon: str


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
