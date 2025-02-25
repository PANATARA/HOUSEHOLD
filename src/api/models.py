# from datetime import datetime
# import re
# import uuid
# from fastapi import HTTPException
# from pydantic import BaseModel, EmailStr, field_validator

# LETTER_MATCH_PATTERN = re.compile(r"^[а-яА-Яa-zA-Z\-]+$")


# class TunedModel(BaseModel):
#     class Config:
#         """tells pydantic to convert even non dict obj to json"""

#         from_attributes = True


# class ShowUser(TunedModel):
#     user_id: uuid.UUID
#     username: str
#     name: str
#     surname: str
#     is_active: bool
#     is_superuser: bool
#     created_at: datetime
#     # updated_at: datetime


# class UserCreate(BaseModel):
#     username: str
#     name: str
#     surname: str
#     password: str

#     @field_validator("name")
#     def validate_name(cls, value):
#         if not LETTER_MATCH_PATTERN.match(value):
#             raise HTTPException(
#                 status_code=422, detail="Name should contains only letters"
#             )
#         return value

#     @field_validator("surname")
#     def validate_surname(cls, value):
#         if not LETTER_MATCH_PATTERN.match(value):
#             raise HTTPException(
#                 status_code=422, detail="Surname should contains only letters"
#             )
#         return value
    
# class UserUpdate(BaseModel):
#     username: str | None = None
#     name: str | None = None
#     surname: str | None = None

#     @field_validator("name")
#     def validate_name(cls, value):
#         if not LETTER_MATCH_PATTERN.match(value):
#             raise HTTPException(
#                 status_code=422, detail="Name should contains only letters"
#             )
#         return value

#     @field_validator("surname")
#     def validate_surname(cls, value):
#         if not LETTER_MATCH_PATTERN.match(value):
#             raise HTTPException(
#                 status_code=422, detail="Surname should contains only letters"
#             )
#         return value
    

# class Token(BaseModel):
#     access_token: str
#     token_type: str
