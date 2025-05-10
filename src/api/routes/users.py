from typing import List, Optional

from auth import User, get_current_active_user
from database import get_supabase_client
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

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
async def get_users(current_user: User = Depends(get_current_active_user)):
    # Simple admin check
    supabase = get_supabase_client()
    response = (
        supabase.from_("users")
        .select("id, email, full_name, is_admin")
        .eq("id", current_user.id)
        .execute()
    )
    if not response.data or not response.data[0].get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    response = supabase.from_("users").select("id, email, full_name").execute()
    return response.data


# Get user by ID
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user: User = Depends(get_current_active_user)):
    # Users can only view themselves unless admin
    if current_user.id != user_id:
        # Check if admin
        supabase = get_supabase_client()
        response = (
            supabase.from_("users")
            .select("is_admin")
            .eq("id", current_user.id)
            .execute()
        )
        if not response.data or not response.data[0].get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )

    supabase = get_supabase_client()
    response = (
        supabase.from_("users")
        .select("id, email, full_name")
        .eq("id", user_id)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return response.data[0]


# Update user
@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
):
    # Users can only update themselves unless admin
    if current_user.id != user_id:
        # Check if admin
        supabase = get_supabase_client()
        response = (
            supabase.from_("users")
            .select("is_admin")
            .eq("id", current_user.id)
            .execute()
        )
        if not response.data or not response.data[0].get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )

    # Update user
    supabase = get_supabase_client()
    update_data = user_update.dict(exclude_unset=True)
    response = supabase.from_("users").update(update_data).eq("id", user_id).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return response.data[0]


# Delete user (admin only or self-delete)
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str, current_user: User = Depends(get_current_active_user)
):
    # Users can only delete themselves unless admin
    if current_user.id != user_id:
        # Check if admin
        supabase = get_supabase_client()
        response = (
            supabase.from_("users")
            .select("is_admin")
            .eq("id", current_user.id)
            .execute()
        )
        if not response.data or not response.data[0].get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )

    # Delete user
    supabase = get_supabase_client()
    response = supabase.from_("users").delete().eq("id", user_id).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return None
