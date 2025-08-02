"""Basic test to verify the setup is working."""

import sys
sys.path.append('.')

import httpx
from src.main import app

def test_health_check():
    """Test that the health check endpoint works."""
    with httpx.Client(app=app, base_url="http://testserver") as client:
        response = client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
        print("✅ Health check endpoint working correctly")

def test_app_creation():
    """Test that the FastAPI app can be created."""
    assert app is not None
    assert app.title == "Voice Authentication Microservice"
    print("✅ FastAPI app created successfully")

if __name__ == "__main__":
    test_app_creation()
    test_health_check()
    print("✅ All basic setup tests passed!")