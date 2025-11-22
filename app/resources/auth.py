from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from typing import Optional
from app.models.auth import GoogleLoginRequest, GoogleLoginResponse, TokenResponse
from app.models.common import ErrorResponse
from app.models.user import UserRead
from app.services.auth_service import AuthService
from app.services.user_service import UserServiceProtocol
from app.utils.settings import get_settings


router = APIRouter()


def get_user_service(request: Request) -> UserServiceProtocol:
    return request.app.state.user_service


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


@router.post(
    "/auth/google",
    response_model=GoogleLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with Google OAuth",
    description="""
    Authenticate user with Google OAuth ID token.
    
    Workflow:
    1. Client sends Google ID token (obtained from Google OAuth flow)
    2. Server verifies the token with Google
    3. Server extracts user information (Google ID, email, name)
    4. Server checks if user exists by Google ID
    5. If user doesn't exist, create new user account
    6. Server generates JWT access token
    7. Server returns user info and JWT token
    
    The client should:
    - Use Google OAuth 2.0 flow to obtain ID token
    - Send the ID token to this endpoint
    - Store the returned JWT token for subsequent API requests
    """,
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
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
                        "is_new_user": False
                    }
                }
            }
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or token",
            "content": {
                "application/json": {
                    "example": {"message": "Invalid Google ID token", "code": 400}
                }
            }
        },
        500: {
            "model": ErrorResponse,
            "description": "Server error",
            "content": {
                "application/json": {
                    "example": {"message": "Internal server error", "code": 500}
                }
            }
        }
    }
)
async def google_login(
    payload: GoogleLoginRequest,
    user_service: UserServiceProtocol = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Google OAuth login endpoint
    
    Execution flow:
    1. Verify Google ID token
    2. Extract user information from token
    3. Check if user exists (by Google ID or email)
    4. Create user if doesn't exist
    5. Generate JWT access token
    6. Return user info and token
    """
    # Step 1: Verify Google ID token
    google_user_info = auth_service.verify_google_token(payload.id_token)
    if not google_user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired Google ID token"
        )
    
    google_id = google_user_info['google_id']
    email = google_user_info['email']
    name = google_user_info.get('name')
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not found in Google token"
        )
    
    # Step 2-3: Check if user exists by Google ID
    user = user_service.get_user_by_google_id(google_id)
    is_new_user = False
    
    # Step 4: If user doesn't exist, check by email (to link existing account)
    if not user:
        user = user_service.get_user_by_email(email)
        # If user exists but doesn't have Google ID, link it
        if user:
            try:
                user = user_service.link_google_id(user.id, google_id)
                auth_service.logger.info("google_id_linked_to_existing_user", user_id=user.id, email=email)
            except Exception as e:
                # Handle potential duplicate Google ID error
                auth_service.logger.error("google_id_link_failed", error=str(e), user_id=user.id)
                # Continue with existing user even if linking fails
    
    # Step 5: Create user if doesn't exist
    if not user:
        try:
            user = user_service.create_user_from_google(
                google_id=google_id,
                email=email,
                name=name
            )
            is_new_user = True
        except Exception as e:
            # Handle potential duplicate email error
            auth_service.logger.error("user_creation_failed", error=str(e), email=email)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user account"
            )
    
    # Step 6: Generate JWT access token
    access_token = auth_service.create_access_token(user.id, user.email, user.role.value)
    expires_in = auth_service.get_token_expires_in()
    
    # Step 7: Build response
    token_response = TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in
    )
    
    user_dict = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "primary_phone": user.primary_phone,
        "role": user.role.value,  # Include role in response
    }
    
    return GoogleLoginResponse(
        user=user_dict,
        token=token_response,
        is_new_user=is_new_user
    )


def get_current_user(
    authorization: Optional[str] = Header(None),
    user_service: UserServiceProtocol = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserRead:
    """
    Dependency to get current authenticated user from JWT token.
    
    Usage:
        @router.get("/protected")
        async def protected_route(user: UserRead = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authorization scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    payload = auth_service.verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user ID from token
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


@router.get(
    "/auth/me",
    response_model=UserRead,
    summary="Get current user",
    description="""
    Get the current authenticated user's information.
    
    This endpoint requires a valid JWT token in the Authorization header.
    Use the token returned from the /auth/google login endpoint.
    
    Headers:
        Authorization: Bearer <jwt_token>
    """,
    responses={
        200: {
            "description": "Current user information",
            "content": {
                "application/json": {
                    "example": {
                        "id": "7e98a8f7-0e22-4f4a-9f3e-5a2d7c6f9e11",
                        "email": "user@example.com",
                        "full_name": "John Doe",
                        "primary_phone": "+1234567890"
                    }
                }
            }
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - Invalid or missing token",
            "content": {
                "application/json": {
                    "example": {"message": "Invalid or expired token", "code": 401}
                }
            }
        }
    }
)
async def get_current_user_info(
    user: UserRead = Depends(get_current_user),
):
    """
    Get current authenticated user information.
    
    This endpoint validates the JWT token and returns the user's information.
    Use this to check if a user is logged in and get their details.
    """
    return user

