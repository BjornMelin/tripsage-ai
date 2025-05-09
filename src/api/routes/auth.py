from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional
from database import get_supabase_client
from auth import create_access_token, Token, User, get_current_active_user
from datetime import timedelta
from passlib.context import CryptContext
import uuid

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
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    supabase = get_supabase_client()
    
    # Find user by email
    response = supabase.from_("users").select("*").eq("email", form_data.username).execute()
    
    if not response.data or not pwd_context.verify(form_data.password, response.data[0]["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = response.data[0]
    
    # Check if user is disabled
    if user.get("is_disabled", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["id"]},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# Register new user
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegister):
    supabase = get_supabase_client()
    
    # Check if email already exists
    email_check = supabase.from_("users").select("id").eq("email", user_data.email).execute()
    if email_check.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user_id = str(uuid.uuid4())
    password_hash = pwd_context.hash(user_data.password)
    
    new_user = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": password_hash,
        "full_name": user_data.full_name,
        "is_admin": False,
        "is_disabled": False
    }
    
    response = supabase.from_("users").insert(new_user).execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create user"
        )
    
    return {"detail": "User created successfully"}

# Get current user profile
@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user