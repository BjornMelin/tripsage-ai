from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from src.api.auth import User, get_current_active_user
from src.api.database import get_repository, get_user_repository
from src.db.repositories.user import UserRepository

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_active_user)],
)


# User models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None


# Get all users (admin only)
@router.get("/", response_model=List[UserResponse])
async def get_users(
    current_user: User = None,
    user_repo: UserRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if user_repo is None:
        user_repo = get_repository(get_user_repository)()

    # Check if current user is admin
    current_user_db = await user_repo.get_by_id(current_user.id)
    if not current_user_db or not current_user_db.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    # Get all users
    users = await user_repo.get_all()
    return [
        UserResponse(id=str(user.id), email=user.email, full_name=user.name)
        for user in users
    ]


# Get user by ID
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = None,
    user_repo: UserRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if user_repo is None:
        user_repo = get_repository(get_user_repository)()

    # Users can only view themselves unless admin
    if current_user.id != user_id:
        # Check if admin
        current_user_db = await user_repo.get_by_id(current_user.id)
        if not current_user_db or not current_user_db.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )

    # Get user
    user = await user_repo.get_by_id(int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse(id=str(user.id), email=user.email, full_name=user.name)


# Update user
@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = None,
    user_repo: UserRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if user_repo is None:
        user_repo = get_repository(get_user_repository)()

    # Users can only update themselves unless admin
    if current_user.id != user_id:
        # Check if admin
        current_user_db = await user_repo.get_by_id(current_user.id)
        if not current_user_db or not current_user_db.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )

    # Get existing user
    user = await user_repo.get_by_id(int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update user fields
    if user_update.full_name is not None:
        user.name = user_update.full_name
    if user_update.email is not None:
        user.email = user_update.email

    # Save updated user
    updated_user = await user_repo.update(user)
    return UserResponse(
        id=str(updated_user.id), email=updated_user.email, full_name=updated_user.name
    )


# Delete user (admin only or self-delete)
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: User = None,
    user_repo: UserRepository = None,
):
    # Get dependencies if not provided
    if current_user is None:
        current_user = await get_current_active_user()
    if user_repo is None:
        user_repo = get_repository(get_user_repository)()

    # Users can only delete themselves unless admin
    if current_user.id != user_id:
        # Check if admin
        current_user_db = await user_repo.get_by_id(current_user.id)
        if not current_user_db or not current_user_db.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )

    # Get user
    user = await user_repo.get_by_id(int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Delete user
    success = await user_repo.delete(user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not delete user"
        )

    return None
