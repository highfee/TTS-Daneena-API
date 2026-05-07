from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    MAIL_USERNAME: str | None = None
    MAIL_PASSWORD: str | None = None
    MAIL_FROM: str
    MAIL_PORT: int | None = None
    MAIL_SERVER: str | None = None
    RESEND_API_KEY: str | None = None
    FORCE_FALLBACK: bool = False

    # Optional OAuth client configuration
    GOOGLE_CLIENT_ID: str | None = None
    MICROSOFT_CLIENT_ID: str | None = None
    APPLE_CLIENT_ID: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
