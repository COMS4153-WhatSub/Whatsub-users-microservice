from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.models.user import UserRead, UserCreate, UserUpdate
from app.models.common import ErrorResponse
from app.services.user_service import UserServiceProtocol
from app.resources.auth import get_current_user


router = APIRouter()


def get_user_service(request: Request) -> UserServiceProtocol:
    return request.app.state.user_service


@router.get(
    "/",
    response_model=List[UserRead],
    summary="List users",
)
async def list_users(service: UserServiceProtocol = Depends(get_user_service)):
    return service.list_users()


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
)
async def create_user(
    payload: UserCreate, service: UserServiceProtocol = Depends(get_user_service)
):
    return service.create_user(payload)


@router.get(
    "/internal/{user_id}",
    response_model=UserRead,
    include_in_schema=False,
    summary="Get user (Internal)",
)
async def get_user_internal(
    user_id: str,
    service: UserServiceProtocol = Depends(get_user_service)
):
    """
    Internal endpoint for microservices to fetch user data without user-level auth.
    Should be protected by network policy or service account in production.
    """
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get a user by ID",
    description="""
    Get user information by ID.
    
    **Authentication Required**: This endpoint requires a valid JWT token.
    Users can only access their own user information.
    """,
    responses={
        200: {
            "description": "User information",
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - Missing or invalid token",
            "content": {
                "application/json": {
                    "example": {"message": "Authorization header missing", "code": 401}
                }
            },
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Cannot access other users' information",
            "content": {
                "application/json": {
                    "example": {"message": "You can only access your own user information", "code": 403}
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {"message": "User not found", "code": 404}
                }
            },
        },
    },
)
async def get_user(
    user_id: str,
    current_user: UserRead = Depends(get_current_user),
    service: UserServiceProtocol = Depends(get_user_service)
):
    """
    Get user by ID endpoint.
    
    Users can only access their own information.
    """
    # Check if user is trying to access their own data
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own user information"
        )
    
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    response = {
      "id": user.id,
      "email": user.email,
      "full_name": user.full_name,
      "primary_phone": user.primary_phone,
      "_links": {
        "self": {
          "href": f"/users/{user.id}"
        },
        "update": {
          "href": f"/users/{user.id}",
          "method": "PATCH",
          "description": "Update this user"
        },
        "delete": {
          "href": f"/users/{user.id}",
          "method": "DELETE",
          "description": "Delete this user"
        },
        "list_subscriptions": {
          "href": f"/userssubscriptions/{user.id}",
          "method": "GET",
          "description": "List this user's subscriptions"
        }
      }
    }
    return response


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Update a user",
    description="""
    Update user information.
    
    **Authentication Required**: This endpoint requires a valid JWT token.
    Users can only update their own information.
    """,
    responses={
        200: {
            "description": "User updated successfully",
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - Missing or invalid token",
            "content": {
                "application/json": {
                    "example": {"message": "Authorization header missing", "code": 401}
                }
            },
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Cannot update other users' information",
            "content": {
                "application/json": {
                    "example": {"message": "You can only update your own user information", "code": 403}
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {"message": "User not found", "code": 404}
                }
            },
        },
    },
)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user: UserRead = Depends(get_current_user),
    service: UserServiceProtocol = Depends(get_user_service)
):
    """
    Update user endpoint.
    
    Users can only update their own information.
    """
    # Check if user is trying to update their own data
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own user information"
        )
    
    user = service.update_user(user_id, payload)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
    description="""
    Delete a user account.
    
    **Authentication Required**: This endpoint requires a valid JWT token.
    Users can only delete their own account.
    """,
    responses={
        204: {
            "description": "User deleted successfully",
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - Missing or invalid token",
            "content": {
                "application/json": {
                    "example": {"message": "Authorization header missing", "code": 401}
                }
            },
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Cannot delete other users' accounts",
            "content": {
                "application/json": {
                    "example": {"message": "You can only delete your own account", "code": 403}
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {"message": "User not found", "code": 404}
                }
            },
        },
    },
)
async def delete_user(
    user_id: str,
    current_user: UserRead = Depends(get_current_user),
    service: UserServiceProtocol = Depends(get_user_service)
):
    """
    Delete user endpoint.
    
    Users can only delete their own account.
    """
    # Check if user is trying to delete their own account
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own account"
        )
    
    ok = service.delete_user(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return None
