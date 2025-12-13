import requests
import pytest
from constants import HTTP_OK, HEALTH_ENDPOINT


@pytest.fixture(scope="session")
def health_endpoint(base_url):
    """Health check endpoint URL"""
    return f"{base_url}{HEALTH_ENDPOINT}"


class TestHealthCheck:
    """Health check endpoint tests - No authentication required"""

    def test_health_check_returns_200(self, health_endpoint):
        """Health check should return HTTP 200 OK"""
        response = requests.get(health_endpoint)
        assert response.status_code == HTTP_OK

    def test_health_check_response_structure(self, health_endpoint):
        """Verify response contains required fields"""
        response = requests.get(health_endpoint)
        data = response.json()
        assert "status" in data
        assert "timestamp" in data

    def test_health_check_status_value(self, health_endpoint):
        """Status field should be 'healthy'"""
        response = requests.get(health_endpoint)
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_no_auth_required(self, health_endpoint):
        """Health check should work without authentication"""
        response = requests.get(health_endpoint)
        assert response.status_code == HTTP_OK

    def test_health_check_consistency(self, health_endpoint):
        """Multiple calls should return consistent results"""
        for _ in range(5):
            response = requests.get(health_endpoint)
            assert response.status_code == HTTP_OK
            assert response.json()["status"] == "healthy"