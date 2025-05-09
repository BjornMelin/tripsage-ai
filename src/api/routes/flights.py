from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from database import get_supabase_client
from auth import get_current_active_user, User

router = APIRouter(
    prefix="/flights",
    tags=["flights"],
    dependencies=[Depends(get_current_active_user)],
)

# Flight models
class FlightBase(BaseModel):
    trip_id: str
    departure_airport: str
    arrival_airport: str
    departure_time: datetime
    arrival_time: datetime
    airline: Optional[str] = None
    flight_number: Optional[str] = None
    price: Optional[float] = None
    seat_class: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class FlightCreate(FlightBase):
    pass

class FlightUpdate(BaseModel):
    departure_airport: Optional[str] = None
    arrival_airport: Optional[str] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    airline: Optional[str] = None
    flight_number: Optional[str] = None
    price: Optional[float] = None
    seat_class: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class FlightResponse(FlightBase):
    id: str
    created_at: str
    updated_at: str

# Verify trip access
async def verify_trip_access(trip_id: str, user_id: str):
    supabase = get_supabase_client()
    response = supabase.from_("trips").select("user_id").eq("id", trip_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    
    if response.data[0]["user_id"] != user_id:
        # Check if admin
        admin_response = supabase.from_("users").select("is_admin").eq("id", user_id).execute()
        if not admin_response.data or not admin_response.data[0].get("is_admin", False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    return True

# Get all flights for a trip
@router.get("/trip/{trip_id}", response_model=List[FlightResponse])
async def get_flights_for_trip(trip_id: str, current_user: User = Depends(get_current_active_user)):
    # Verify access to trip
    await verify_trip_access(trip_id, current_user.id)
    
    # Get flights
    supabase = get_supabase_client()
    response = supabase.from_("flights").select("*").eq("trip_id", trip_id).execute()
    
    return response.data

# Get flight by ID
@router.get("/{flight_id}", response_model=FlightResponse)
async def get_flight(flight_id: str, current_user: User = Depends(get_current_active_user)):
    supabase = get_supabase_client()
    response = supabase.from_("flights").select("*").eq("id", flight_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found")
    
    # Verify access to flight's trip
    await verify_trip_access(response.data[0]["trip_id"], current_user.id)
    
    return response.data[0]

# Create new flight
@router.post("/", response_model=FlightResponse, status_code=status.HTTP_201_CREATED)
async def create_flight(flight: FlightCreate, current_user: User = Depends(get_current_active_user)):
    # Verify access to trip
    await verify_trip_access(flight.trip_id, current_user.id)
    
    # Create flight
    supabase = get_supabase_client()
    response = supabase.from_("flights").insert(flight.dict()).execute()
    
    if not response.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not create flight")
    
    return response.data[0]

# Update flight
@router.patch("/{flight_id}", response_model=FlightResponse)
async def update_flight(
    flight_id: str, 
    flight_update: FlightUpdate, 
    current_user: User = Depends(get_current_active_user)
):
    # Check if flight exists
    supabase = get_supabase_client()
    response = supabase.from_("flights").select("*").eq("id", flight_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found")
    
    # Verify access to flight's trip
    await verify_trip_access(response.data[0]["trip_id"], current_user.id)
    
    # Update flight
    update_data = flight_update.dict(exclude_unset=True)
    update_response = supabase.from_("flights").update(update_data).eq("id", flight_id).execute()
    
    if not update_response.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not update flight")
    
    return update_response.data[0]

# Delete flight
@router.delete("/{flight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flight(flight_id: str, current_user: User = Depends(get_current_active_user)):
    # Check if flight exists
    supabase = get_supabase_client()
    response = supabase.from_("flights").select("*").eq("id", flight_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found")
    
    # Verify access to flight's trip
    await verify_trip_access(response.data[0]["trip_id"], current_user.id)
    
    # Delete flight
    delete_response = supabase.from_("flights").delete().eq("id", flight_id).execute()
    
    return None