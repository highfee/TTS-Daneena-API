from datetime import datetime, timedelta
from typing import Literal

import requests
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app import db
from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.auth_token import AuthToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    AuthStartRequest,
    AuthStartResponse,
    AuthVerifyRequest,
    AuthVerifyResponse,
    OAuthTokenPayload,
)
from app.services.email import send_auth_email
from app.utils.tokens import generate_auth_token
from app.utils.tokens import generate_refresh_token

# from app.core.security import create_refresh_token

router = APIRouter(prefix="/auth", tags=["Auth"])


# start auth endpoint with rate limiting
@router.post("/start", response_model=AuthStartResponse)
@limiter.limit("5/minute")
async def auth_start(
    payload: AuthStartRequest, request: Request, db: Session = Depends(get_db)
):
    email = payload.email.lower()

    # 1. Find or create user
    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Generate token
    token = generate_auth_token()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    auth_token = AuthToken(user_id=user.id, token=token, expires_at=expires_at)

    db.add(auth_token)
    db.commit()

    # 3. Send email
    await send_auth_email(email=email, token=token)

    return {"message": "Authentication code sent to email"}


# verify auth endpoint with rate limiting
@router.post("/verify", response_model=AuthVerifyResponse)
@limiter.limit("10/minute")
def auth_verify(
    payload: AuthVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
    response: Response = None,
):
    email = payload.email.lower()
    token = payload.token

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    auth_token = (
        db.query(AuthToken)
        .filter(AuthToken.user_id == user.id, AuthToken.token == token)
        .first()
    )

    if not auth_token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    if auth_token.used:
        raise HTTPException(status_code=400, detail="Token already used")

    if auth_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")

    # Mark token as used
    auth_token.used = True
    db.commit()

    # Issue JWT
    access_token = create_access_token(subject=str(user.id))
    refresh_token_value = generate_refresh_token()

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_value,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )

    db.add(refresh_token)
    db.commit()

    response.set_cookie(
        key="refresh_token",
        value=refresh_token_value,
        httponly=True,
        secure=False,   # Set True in production (HTTPS only)
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )

    return {
        "user_id": str(user.id),
        "access_token": access_token,
        "refresh_token": refresh_token_value,
        "token_type": "bearer",
    }


@router.post("/refresh")
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Read refresh token from httpOnly cookie, validate, rotate, and return a new access token."""
    refresh_token_value = request.cookies.get("refresh_token")

    if not refresh_token_value:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token == refresh_token_value,
            RefreshToken.revoked == False,
        )
        .first()
    )

    if not token or token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # --- Token Rotation ---
    # 1. Revoke the old token
    token.revoked = True

    # 2. Issue a new refresh token
    new_refresh_value = generate_refresh_token()
    new_refresh = RefreshToken(
        user_id=token.user_id,
        token=new_refresh_value,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(new_refresh)
    db.commit()

    # 3. Set the new refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_value,
        httponly=True,
        secure=False,   # Set True in production (HTTPS only)
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )

    # 4. Issue a new access token
    access_token = create_access_token(subject=str(token.user_id))
    return {"access_token": access_token, "token_type": "bearer"}


def _get_email_from_google(access_token: str) -> str:
    resp = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer ${access_token}"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to verify Google token")
    data = resp.json()
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google account email not found")
    return email.lower()


def _get_email_from_microsoft(access_token: str) -> str:
    resp = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=400, detail="Failed to verify Microsoft token"
        )
    data = resp.json()
    # Microsoft Graph can return email in different fields depending on account type
    email = (
        data.get("mail")
        or data.get("userPrincipalName")
        or (data.get("otherMails") or [None])[0]
    )
    if not email:
        raise HTTPException(
            status_code=400, detail="Microsoft account email not found"
        )
    return email.lower()


def _get_email_from_apple(id_token: str) -> str:
    from jose import jwt

    try:
        # For now we only parse claims without signature verification.
        # For production, you should verify the signature and audience using Apple's keys.
        claims = jwt.get_unverified_claims(id_token)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Apple identity token")

    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Apple account email not found")
    return email.lower()


def _get_email_from_oauth(
    provider: Literal["google", "apple", "microsoft"], payload: OAuthTokenPayload
) -> str:
    provider = provider.lower()
    if provider == "google":
        if not payload.access_token:
            raise HTTPException(
                status_code=400, detail="Google access_token is required"
            )
        return _get_email_from_google(payload.access_token)
    if provider == "microsoft":
        if not payload.access_token:
            raise HTTPException(
                status_code=400, detail="Microsoft access_token is required"
            )
        return _get_email_from_microsoft(payload.access_token)
    if provider == "apple":
        if not payload.id_token:
            raise HTTPException(status_code=400, detail="Apple id_token is required")
        return _get_email_from_apple(payload.id_token)

    raise HTTPException(status_code=400, detail="Unsupported OAuth provider")


@router.post("/oauth/{provider}", response_model=AuthVerifyResponse)
def oauth_login(
    provider: Literal["google", "apple", "microsoft"],
    payload: OAuthTokenPayload,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    OAuth login endpoint for Google, Apple, and Microsoft.
    The frontend is responsible for completing the provider-specific OAuth flow
    and sending an access_token (Google, Microsoft) or id_token (Apple) here.
    """
    email = _get_email_from_oauth(provider, payload)

    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Issue JWT + refresh token, reusing existing email-code auth logic
    access_token = create_access_token(subject=str(user.id))
    refresh_token_value = generate_refresh_token()

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_value,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )

    db.add(refresh_token)
    db.commit()

    response.set_cookie(
        key="refresh_token",
        value=refresh_token_value,
        httponly=True,
        secure=False,  # Set True in production (HTTPS only)
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )

    return {
        "user_id": str(user.id),
        "access_token": access_token,
        "refresh_token": refresh_token_value,
        "token_type": "bearer",
    }
