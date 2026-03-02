from pydantic import BaseModel, EmailStr


class AuthStartRequest(BaseModel):
    email: EmailStr


class AuthStartResponse(BaseModel):
    message: str


class AuthVerifyRequest(BaseModel):
    email: EmailStr
    token: str


class AuthVerifyResponse(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
