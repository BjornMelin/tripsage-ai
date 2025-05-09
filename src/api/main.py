from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from routes import users, trips, flights, auth

# Initialize environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="TripSage API",
    description="API for TripSage travel planning system",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trips.router)
app.include_router(flights.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)