from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = Field(default="whatsub-users")
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    port: int = Field(default=8080)
    
    # Database settings
    db_host: str | None = Field(default=None)
    db_port: int = Field(default=3306)
    db_user: str | None = Field(default=None)
    db_pass: str | None = Field(default=None)
    db_name: str | None = Field(default=None)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
