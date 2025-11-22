"""
Authentication service for Google OAuth and JWT token management
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from google.auth.transport import requests
from google.oauth2 import id_token

from app.utils.settings import Settings


class AuthService:
    """Service for handling authentication with Google OAuth and JWT tokens"""
    
    def __init__(self, settings: Settings, logger):
        self.settings = settings
        self.logger = logger
        self.google_client_id = settings.google_client_id
    
    def verify_google_token(self, id_token_str: str) -> Optional[Dict[str, Any]]:
        """
        Verify Google ID token and extract user information
        
        Args:
            id_token_str: Google ID token string
            
        Returns:
            Dictionary with user information (sub, email, name, etc.) or None if invalid
        """
        try:
            if not self.google_client_id:
                self.logger.error("google_client_id_not_configured")
                raise ValueError("Google OAuth client ID is not configured")
            
            # Verify the token
            request = requests.Request()
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                request,
                self.google_client_id
            )
            
            # Verify the issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                self.logger.warning("invalid_token_issuer", issuer=idinfo.get('iss'))
                return None
            
            # Extract user information
            user_info = {
                'google_id': idinfo['sub'],  # Google user ID
                'email': idinfo.get('email'),
                'name': idinfo.get('name'),
                'picture': idinfo.get('picture'),
                'email_verified': idinfo.get('email_verified', False),
            }
            
            self.logger.info("google_token_verified", google_id=user_info['google_id'], email=user_info['email'])
            return user_info
            
        except ValueError as e:
            # Invalid token
            self.logger.error("google_token_verification_failed", error=str(e))
            return None
        except Exception as e:
            self.logger.error("google_token_verification_error", error=str(e), error_type=type(e).__name__)
            return None
    
    def create_access_token(self, user_id: str, email: str, role: str = "user") -> str:
        """
        Create JWT access token for authenticated user
        
        Args:
            user_id: User ID
            email: User email
            role: User role (user or admin)
            
        Returns:
            JWT token string
        """
        expire = datetime.utcnow() + timedelta(minutes=self.settings.jwt_access_token_expire_minutes)
        
        payload = {
            "sub": user_id,  # Subject (user ID)
            "email": email,
            "role": role,  # User role
            "exp": expire,  # Expiration time
            "iat": datetime.utcnow(),  # Issued at
        }
        
        token = jwt.encode(
            payload,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm
        )
        
        self.logger.info("access_token_created", user_id=user_id, role=role)
        return token
    
    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT access token and extract payload
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary with token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            self.logger.warning("token_expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning("invalid_token", error=str(e))
            return None
        except Exception as e:
            self.logger.error("token_verification_error", error=str(e), error_type=type(e).__name__)
            return None
    
    def get_token_expires_in(self) -> int:
        """Get token expiration time in seconds"""
        return self.settings.jwt_access_token_expire_minutes * 60

