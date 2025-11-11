from pydantic import BaseModel

from users.schemas import UserResponseSchema


class MeProfileSchema(BaseModel):
    user: UserResponseSchema


class UserProfileSchema(BaseModel):
    user: UserResponseSchema
