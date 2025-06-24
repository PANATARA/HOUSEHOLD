from pydantic import BaseModel


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
