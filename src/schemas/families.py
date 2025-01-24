from datetime import datetime
import re
import uuid
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr, field_validator

LETTER_MATCH_PATTERN = re.compile(r"^[а-яА-Яa-zA-Z\-]+$")


class TunedModel(BaseModel):
    class Config:
        """tells pydantic to convert even non dict obj to json"""

        from_attributes = True

class FamilyCreate(BaseModel):
    name: str

class FamilyShow(BaseModel):
    name: str