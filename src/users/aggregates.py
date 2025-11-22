from pydantic import BaseModel

from users.schemas import UserResponseSchema


class MeProfileSchema(BaseModel):
    user: UserResponseSchema
    is_family_member: bool
    is_family_admin: bool


class UserProfileSchema(BaseModel):
    user: UserResponseSchema
