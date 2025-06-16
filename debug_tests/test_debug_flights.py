"""Debug test for flights router."""
from fastapi.testclient import TestClient
from fastapi import status
import json

# Import the app directly
from tripsage.api.main import app

# Create a test client
client = TestClient(app)

# Test data
flight_search_data = {
    "origin": "LAX",
    "destination": "NRT",
    "departure_date": "2024-03-15",
    "return_date": "2024-03-22",
    "adults": 1,
    "children": 0,
    "infants": 0,
    "cabin_class": "economy",
}

# Make the request
response = client.post(
    "/api/flights/search",
    json=flight_search_data,
    headers={"Authorization": "Bearer fake-token"}
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")