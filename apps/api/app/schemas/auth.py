from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRead(BaseModel):
    id: str
    full_name: str
    email: EmailStr


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    device_id: str | None = Field(default=None, max_length=255)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(TokenPair):
    user: UserRead


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(..., min_length=20)
    device_id: str | None = Field(default=None, max_length=255)


class RefreshTokenResponse(TokenPair):
    pass


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(..., min_length=20)


class LogoutResponse(BaseModel):
    success: bool



class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class PasswordResetRequestResponse(BaseModel):
    success: bool
    message: str
    development_reset_token: str | None = None


class PasswordResetConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., min_length=20)
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetConfirmResponse(BaseModel):
    success: bool
