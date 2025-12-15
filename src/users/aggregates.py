from pydantic import BaseModel

from users.schemas import UserResponseSchema, UserResponseSchemaFull


class MeProfileSchema(BaseModel):
    user: UserResponseSchemaFull
    is_family_member: bool
    is_family_admin: bool


class UserProfileSchema(BaseModel):
    user: UserResponseSchema
