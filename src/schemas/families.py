from datetime import datetime, timedelta
import re
from pydantic import BaseModel

from schemas.users import ShowUser

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
    members: list[ShowUser]

    class Config:
        orm_mode = True
        from_attributes = True 


class UserInviteParametr(BaseModel):
    should_confirm_chorelog: bool
    should_confirm_creating_chore: bool
    can_create_chore: bool
    can_change_family_name: bool
    can_kick_user: bool
    can_invite_users: bool
    can_promote_user: bool


class InviteToken(BaseModel):
    invite_token: str
    life_time: timedelta


class JoinFamily(BaseModel):
    invite_token: str