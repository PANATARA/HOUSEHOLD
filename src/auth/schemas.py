from pydantic import BaseModel, Field


class AccessRefreshTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    is_new_user: bool
    is_family_member: bool


class RefreshToken(BaseModel):
    refresh_token: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str


class LoginSchema(BaseModel):
    username: str = Field(..., min_length=1, max_length=60)
    password: str = Field(..., min_length=1)


class RegisterSchema(BaseModel):
    username: str = Field(..., min_length=2, max_length=60)
    password: str = Field(..., min_length=6)
    name: str | None = Field(default=None, max_length=50)
    icon: str | None = Field(default=None, max_length=100)
    icon_color: str | None = Field(default=None, max_length=50)
    icon_bg: str | None = Field(default=None, max_length=100)


class DebugAuthModel(BaseModel):
    username: str = "debug_user"


class GoogleAuthSchema(BaseModel):
    credential: str | None = None
    token: str | None = None

    def get_token(self) -> str:
        t = self.credential or self.token
        if not t:
            raise ValueError("Google ID Token ('credential' or 'token') is required")
        return t
