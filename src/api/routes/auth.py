from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from src.api.auth import Token, User, create_access_token, get_current_active_user
from src.api.database import get_repository, get_user_repository
from src.db.models.user import User as DBUser
from src.db.repositories.user import UserRepository

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# User registration model
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


# Login
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo: UserRepository = Depends(get_repository(get_user_repository)),
):
    # Find user by email
    user = await user_repo.get_by_email(form_data.username)

    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is disabled
    if user.is_disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


# Register new user
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    user_repo: UserRepository = Depends(get_repository(get_user_repository)),
):
    # Check if email already exists
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user
    password_hash = pwd_context.hash(user_data.password)

    new_user = DBUser(
        email=user_data.email,
        name=user_data.full_name,
        password_hash=password_hash,
        is_admin=False,
        is_disabled=False,
    )

    await user_repo.create(new_user)

    return {"detail": "User created successfully"}


# Get current user profile
@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user
