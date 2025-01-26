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