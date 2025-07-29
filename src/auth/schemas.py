from pydantic import BaseModel, field_validator

from config import MAX_VERIFY_CODE, MIN_VERIFY_CODE


class AccessRefreshTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    is_new_user: bool


class RefreshToken(BaseModel):
    refresh_token: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str


class AuthEmail(BaseModel):
    email: str


class AuthCodeEmail(BaseModel):
    email: str
    code: int

    @field_validator("code")
    def validate_code(cls, v):
        if v < MIN_VERIFY_CODE or v > MAX_VERIFY_CODE:
            raise ValueError("Code must be exactly 6 digits")
        return v
