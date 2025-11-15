from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = Field(default="whatsub-users")
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    port: int = Field(default=8080, alias="PORT")
    
    # Database settings
    db_host: str | None = Field(default="10.63.160.5")
    db_port: int = Field(default=3306)
    db_user: str | None = Field(default='whatsub')
    db_pass: str | None = Field(default='WhatSub123!')
    db_name: str | None = Field(default='whatsub')
    
    # Google OAuth settings
    google_client_id: str | None = Field(default=None, description="Google OAuth 2.0 Client ID")
    google_client_secret: str | None = Field(default=None, description="Google OAuth 2.0 Client Secret")
    
    # JWT settings
    jwt_secret_key: str = Field(default="your-secret-key-change-in-production", description="Secret key for JWT token signing")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(default=30, description="JWT access token expiration time in minutes")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
