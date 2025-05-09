import os
from pydantic import BaseModel
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AgentConfig(BaseModel):
    """Configuration settings for TripSage agents"""
    
    # OpenAI configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    model_name: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    max_tokens: int = int(os.getenv("MAX_TOKENS", "4096"))
    temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
    
    # Supabase configuration
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    
    # Travel API configuration
    flight_api_key: Optional[str] = os.getenv("FLIGHT_API_KEY", "")
    hotel_api_key: Optional[str] = os.getenv("HOTEL_API_KEY", "")
    
    # Agent settings
    agent_timeout: int = int(os.getenv("AGENT_TIMEOUT", "120"))  # seconds
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    agent_memory_size: int = int(os.getenv("AGENT_MEMORY_SIZE", "10"))  # number of messages
    
    # Default agent parameters
    default_flight_preferences: Dict[str, Any] = {
        "seat_class": "economy",
        "max_stops": 1,
        "preferred_airlines": [],
        "avoid_airlines": [],
        "time_window": "flexible"
    }
    
    default_accommodation_preferences: Dict[str, Any] = {
        "property_type": "hotel",
        "min_rating": 3.5,
        "amenities": ["wifi", "breakfast"],
        "location_preference": "city_center"
    }

    # Helper functions
    def validate_credentials(self) -> bool:
        """Validate that all required credentials are provided"""
        if not self.openai_api_key:
            print("Missing OpenAI API key")
            return False
        if not self.supabase_url or not self.supabase_key:
            print("Missing Supabase credentials")
            return False
        return True
    
    def get_flight_preferences(self, user_preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Merge default flight preferences with user preferences"""
        if user_preferences is None:
            return self.default_flight_preferences
        
        merged = self.default_flight_preferences.copy()
        merged.update(user_preferences)
        return merged
    
    def get_accommodation_preferences(self, user_preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Merge default accommodation preferences with user preferences"""
        if user_preferences is None:
            return self.default_accommodation_preferences
        
        merged = self.default_accommodation_preferences.copy()
        merged.update(user_preferences)
        return merged

# Create a default config instance
config = AgentConfig()

# Verify configuration on import
if not config.validate_credentials():
    print("Warning: Some required credentials are missing. Agents may not function correctly.")