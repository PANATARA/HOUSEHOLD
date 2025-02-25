from datetime import datetime
import re
from uuid import UUID
from fastapi import HTTPException
from pydantic import BaseModel, field_validator

LETTER_MATCH_PATTERN = re.compile(r"^[а-яА-Яa-zA-Z\-]+$")


class TunedModel(BaseModel):
    class Config:
        """tells pydantic to convert even non dict obj to json"""

        from_attributes = True


class UserResponse(TunedModel):
    id: UUID
    username: str 
    name: str
    surname: str

    class Config:
        orm_mode = True
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    name: str
    surname: str
    password: str

    @field_validator("name")
    def validate_name(cls, value):
        if not LETTER_MATCH_PATTERN.match(value):
            raise HTTPException(
                status_code=422, detail="Name should contains only letters"
            )
        return value

    @field_validator("surname")
    def validate_surname(cls, value):
        if not LETTER_MATCH_PATTERN.match(value):
            raise HTTPException(
                status_code=422, detail="Surname should contains only letters"
            )
        return value


class UserUpdate(BaseModel):
    username: str | None = None
    name: str | None = None
    surname: str | None = None

    @field_validator("name")
    def validate_name(cls, value):
        if not LETTER_MATCH_PATTERN.match(value):
            raise HTTPException(
                status_code=422, detail="Name should contains only letters"
            )
        return value

    @field_validator("surname")
    def validate_surname(cls, value):
        if not LETTER_MATCH_PATTERN.match(value):
            raise HTTPException(
                status_code=422, detail="Surname should contains only letters"
            )
        return value
    

class UserFamilyPermissionModel(BaseModel):
    should_confirm_chore_completion: bool


class UserSettingsShow(BaseModel):
    user_id: UUID
    app_theme: str


class UserDetail(BaseModel):
    id: UUID
    username:str
    name: str
    surname: str
    created_at: datetime
    updated_at: datetime