from typing import Optional
from pydantic import BaseModel, Field


class GoogleLoginRequest(BaseModel):
    """Google OAuth login request"""
    id_token: str = Field(description="Google ID token from OAuth flow")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1Njc4OTAifQ..."
                }
            ]
        }
    }


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration time in seconds")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 1800
                }
            ]
        }
    }


class GoogleLoginResponse(BaseModel):
    """Google login response"""
    user: dict = Field(description="User information")
    token: TokenResponse = Field(description="JWT token information")
    is_new_user: bool = Field(description="Whether this is a newly registered user")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user": {
                        "id": "7e98a8f7-0e22-4f4a-9f3e-5a2d7c6f9e11",
                        "email": "user@example.com",
                        "full_name": "John Doe"
                    },
                    "token": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 1800
                    },
                    "is_new_user": True
                }
            ]
        }
    }

