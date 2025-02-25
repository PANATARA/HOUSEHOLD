from datetime import datetime, timedelta
import re
from pydantic import BaseModel

from schemas.users import UserResponse

LETTER_MATCH_PATTERN = re.compile(r"^[а-яА-Яa-zA-Z\-]+$")


class TunedModel(BaseModel):
    class Config:
        """tells pydantic to convert even non dict obj to json"""

        from_attributes = True

class FamilyCreate(BaseModel):
    name: str

class FamilyShow(BaseModel):
    name: str

class FamilyFullShow(BaseModel):
    name: str
    members: list[UserResponse]

    class Config:
        orm_mode = True
        from_attributes = True 


class UserInviteParametr(BaseModel):
    should_confirm_chore_completion: bool


class InviteToken(BaseModel):
    invite_token: str
    life_time: timedelta


class JoinFamily(BaseModel):
    invite_token: str