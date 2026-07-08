from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from users.schemas import UserResponseSchema, UserResponseSchemaFull


class FamilyCreateSchema(BaseModel):
    """Schema for creating a new family"""

    name: str
    icon: str


class FamilyResponseSchema(BaseModel):
    id: UUID
    name: str
    icon: str
    icon_color: str
    icon_bg: str
    experience: int

    model_config = ConfigDict(from_attributes=True)


class FamilyUpdateSchema(BaseModel):
    name: str | None = None
    icon: str | None = None
    icon_color: str | None = None
    icon_bg: str | None = None

    @field_validator("name", "icon", "icon_color", "icon_bg", mode="before")
    @classmethod
    def field_not_none(cls, value, info):
        if value is None:
            raise ValueError(f"{info.field_name} cannot be null")
        return value


class FamilyMembersSchema(BaseModel):
    members: list[UserResponseSchemaFull]


class FamilyMemberStatsSchema(BaseModel):
    member: UserResponseSchema | None
    chore_completion_count: int | None


class FamilyJoinSchema(BaseModel):
    invite_token: str


class InviteTokenSchema(BaseModel):
    invite_token: str
    ttl: int
