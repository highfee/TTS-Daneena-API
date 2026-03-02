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


class OAuthTokenPayload(BaseModel):
    """
    Generic OAuth payload posted from the frontend after successful provider login.
    For providers that expose a userinfo endpoint (Google, Microsoft) an access_token
    is sufficient. For providers that primarily return an ID token (Apple), id_token
    can be used to extract the email.
    """

    access_token: str | None = None
    id_token: str | None = None
