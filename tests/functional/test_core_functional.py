import allure
import pytest
import requests
from allure_commons.types import AttachmentType
from constants import (
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
    HTTP_OK,
    REQUEST_TIMEOUT,
)
from conftest import SSL_VERIFY
from config.logger_config import get_test_logger

logger = get_test_logger()

if not SSL_VERIFY:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@allure.feature("API Functional Tests")
@allure.story("Endpoints 1-5: Message-based Response")
@pytest.mark.parametrize("endpoint", [
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
])
@pytest.mark.core_functional
class TestEndpointsWithMessage:
    """Tests for endpoints that return message-based responses"""

    @allure.title("Endpoint supports GET method")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("happy-path", "core")
    def test_endpoint_supports_get_method(self, base_url, headers, endpoint):
        """Verify endpoint accepts GET requests"""
        with allure.step(f"Send GET request to {endpoint}"):
            response = requests.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify GET method is supported"):
            assert response.status_code == HTTP_OK, \
                f"GET not supported. Status: {response.status_code}"
            allure.attach(
                f"Method: GET\nStatus: {response.status_code}",
                name="Method Support",
                attachment_type=AttachmentType.TEXT
            )

    @allure.title("Valid token returns successful response")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("happy-path", "authentication", "core")
    def test_endpoint_returns_200_with_valid_token(self, base_url, headers, endpoint):
        """Verify endpoint returns 200 OK with valid token"""
        with allure.step(f"Send GET request to {endpoint}"):
            response = requests.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify status is 200 OK"):
            assert response.status_code == HTTP_OK, \
                f"Expected {HTTP_OK}, got {response.status_code}"
            allure.attach(
                f"Status Code: {response.status_code}",
                name="Status Verification",
                attachment_type=AttachmentType.TEXT
            )

    @allure.title("Response contains valid JSON")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("happy-path", "response-validation")
    def test_endpoint_returns_valid_json(self, base_url, headers, endpoint):
        """Verify response is valid JSON"""
        with allure.step(f"Send GET request to {endpoint}"):
            response = requests.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify response is valid JSON"):
            try:
                data = response.json()
                allure.attach(
                    f"Valid JSON:\n{response.text}",
                    name="JSON Response",
                    attachment_type=AttachmentType.TEXT
                )
            except ValueError as e:
                pytest.fail(f"Invalid JSON: {str(e)}")

    @allure.title("Response contains required fields")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("response-validation", "core")
    def test_endpoint_has_required_fields(self, base_url, headers, endpoint):
        """Verify response has message, status, timestamp fields"""
        with allure.step(f"Send GET request to {endpoint}"):
            response = requests.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )
            data = response.json()

        with allure.step("Verify all required fields present"):
            required_fields = ["message", "status", "timestamp"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            allure.attach(
                f"Fields found:\n- message: {data.get('message')}\n- status: {data.get('status')}\n- timestamp: {data.get('timestamp')}",
                name="Required Fields",
                attachment_type=AttachmentType.TEXT
            )

    @allure.title("Status field value is 'success'")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("response-validation")
    def test_endpoint_status_is_success(self, base_url, headers, endpoint):
        """Verify status field equals 'success'"""
        with allure.step(f"Send GET request to {endpoint}"):
            response = requests.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )
            data = response.json()

        with allure.step("Verify status is 'success'"):
            assert data["status"] == "success", \
                f"Expected 'success', got '{data['status']}'"
            allure.attach(
                f"Status: {data['status']}",
                name="Status Value",
                attachment_type=AttachmentType.TEXT
            )

    @allure.title("Response body is not empty")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("response-validation")
    def test_endpoint_response_body_not_empty(self, base_url, headers, endpoint):
        """Verify response contains data"""
        with allure.step(f"Send GET request to {endpoint}"):
            response = requests.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify response body is not empty"):
            assert response.text, "Response body is empty"
            assert len(response.content) > 0, "Response has no content"
            allure.attach(
                f"Response size: {len(response.content)} bytes",
                name="Body Size",
                attachment_type=AttachmentType.TEXT
            )

    @allure.title("Response has required headers")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("headers", "response-validation")
    def test_endpoint_response_has_required_headers(self, base_url, headers, endpoint):
        """Verify response includes content-type and other required headers"""
        with allure.step(f"Send GET request to {endpoint}"):
            response = requests.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify required headers present"):
            required_headers = ["content-type"]
            for header in required_headers:
                assert header in response.headers, \
                    f"Missing required header: {header}"

            allure.attach(
                f"Headers:\n{chr(10).join([f'{k}: {v}' for k, v in response.headers.items()])}",
                name="Response Headers",
                attachment_type=AttachmentType.TEXT
            )

    @allure.title("Response has correct encoding")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("response-validation")
    def test_endpoint_response_encoding(self, base_url, headers, endpoint):
        """Verify response is UTF-8 encoded"""
        with allure.step(f"Send GET request to {endpoint}"):
            response = requests.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify encoding is UTF-8"):
            assert response.encoding in ["utf-8", "UTF-8"], \
                f"Expected UTF-8, got {response.encoding}"
            allure.attach(
                f"Encoding: {response.encoding}",
                name="Response Encoding",
                attachment_type=AttachmentType.TEXT
            )

    @allure.title("Response time within acceptable limits")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("performance", "reliability")
    def test_endpoint_response_time_acceptable(self, base_url, headers, endpoint):
        """Verify endpoint responds within 5 seconds"""
        with allure.step(f"Send GET request to {endpoint}"):
            response = requests.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify response time < 5 seconds"):
            response_time = response.elapsed.total_seconds()
            max_time = 5.0

            assert response_time < max_time, \
                f"Response took {response_time:.3f}s, exceeds {max_time}s limit"

            allure.attach(
                f"Response time: {response_time:.3f}s\nMax allowed: {max_time}s",
                name="Performance",
                attachment_type=AttachmentType.TEXT
            )

    @allure.title("Multiple calls return consistent status")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("consistency", "reliability")
    def test_endpoint_consistency_multiple_calls(self, base_url, headers, endpoint):
        """Verify endpoint returns same status on 3 successive calls"""
        statuses = []

        with allure.step("Make 3 successive requests"):
            for i in range(3):
                with allure.step(f"Call {i + 1}"):
                    response = requests.get(
                        f"{base_url}{endpoint}",
                        headers=headers,
                        verify=SSL_VERIFY,
                        timeout=REQUEST_TIMEOUT
                    )
                    statuses.append(response.status_code)

        with allure.step("Verify all calls returned same status"):
            assert len(set(statuses)) == 1, \
                f"Inconsistent statuses: {statuses}"

            allure.attach(
                f"All 3 calls returned: {statuses[0]}",
                name="Consistency Check",
                attachment_type=AttachmentType.TEXT
            )


@allure.feature("API Functional Tests")
@allure.story("Endpoint 6: Nested Data Structure")
@pytest.mark.core_functional
class TestEndpoint6:
    """Tests for /api/test/6 with nested data object"""

    @allure.title("Endpoint 6 supports GET method")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("happy-path", "core")
    def test_endpoint_6_supports_get(self, base_url, headers):
        """Verify endpoint 6 accepts GET requests"""
        with allure.step("Send GET request"):
            response = requests.get(
                f"{base_url}{TEST_ENDPOINT_6}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify GET method is supported"):
            assert response.status_code == HTTP_OK
            allure.attach(
                f"Method: GET\nStatus: {response.status_code}",
                name="Method Support",
                attachment_type=AttachmentType.TEXT
            )

    @allure.title("Endpoint 6 returns 200 with valid token")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("happy-path", "authentication")
    def test_endpoint_6_returns_200(self, base_url, headers):
        """Verify endpoint 6 returns 200 OK"""
        with allure.step("Send GET request"):
            response = requests.get(
                f"{base_url}{TEST_ENDPOINT_6}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify status is 200"):
            assert response.status_code == HTTP_OK

    @allure.title("Endpoint 6 response is valid JSON")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("response-validation")
    def test_endpoint_6_valid_json(self, base_url, headers):
        """Verify endpoint 6 returns valid JSON"""
        with allure.step("Send GET request"):
            response = requests.get(
                f"{base_url}{TEST_ENDPOINT_6}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify response is valid JSON"):
            try:
                data = response.json()
                allure.attach(
                    f"Valid JSON:\n{response.text}",
                    name="JSON Response",
                    attachment_type=AttachmentType.TEXT
                )
            except ValueError as e:
                pytest.fail(f"Invalid JSON: {str(e)}")

    @allure.title("Endpoint 6 has data object with required fields")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("response-validation", "core")
    def test_endpoint_6_data_structure(self, base_url, headers):
        """Verify endpoint 6 has data object with count, id, value"""
        with allure.step("Send GET request"):
            response = requests.get(
                f"{base_url}{TEST_ENDPOINT_6}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )
            data = response.json()

        with allure.step("Verify data structure"):
            assert "data" in data, "Missing data field"
            assert "status" in data, "Missing status field"
            assert "timestamp" in data, "Missing timestamp field"

            data_obj = data["data"]
            assert "count" in data_obj, "Missing count in data"
            assert "id" in data_obj, "Missing id in data"
            assert "value" in data_obj, "Missing value in data"

            allure.attach(
                f"Data structure:\n- count: {data_obj['count']}\n- id: {data_obj['id']}\n- value: {data_obj['value']}",
                name="Data Fields",
                attachment_type=AttachmentType.TEXT
            )

    @allure.title("Endpoint 6 status is 'success'")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("response-validation")
    def test_endpoint_6_status_success(self, base_url, headers):
        """Verify status field equals 'success'"""
        with allure.step("Send GET request"):
            response = requests.get(
                f"{base_url}{TEST_ENDPOINT_6}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )
            data = response.json()

        with allure.step("Verify status is 'success'"):
            assert data["status"] == "success", \
                f"Expected 'success', got '{data['status']}'"

    @allure.title("Endpoint 6 response body not empty")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("response-validation")
    def test_endpoint_6_body_not_empty(self, base_url, headers):
        """Verify response contains data"""
        with allure.step("Send GET request"):
            response = requests.get(
                f"{base_url}{TEST_ENDPOINT_6}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify response body not empty"):
            assert response.text, "Response body is empty"
            assert len(response.content) > 0, "Response has no content"

    @allure.title("Endpoint 6 has required headers")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("headers")
    def test_endpoint_6_required_headers(self, base_url, headers):
        """Verify response includes required headers"""
        with allure.step("Send GET request"):
            response = requests.get(
                f"{base_url}{TEST_ENDPOINT_6}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify headers present"):
            assert "content-type" in response.headers

    @allure.title("Endpoint 6 response encoding is UTF-8")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("response-validation")
    def test_endpoint_6_encoding(self, base_url, headers):
        """Verify response is UTF-8 encoded"""
        with allure.step("Send GET request"):
            response = requests.get(
                f"{base_url}{TEST_ENDPOINT_6}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify UTF-8 encoding"):
            assert response.encoding in ["utf-8", "UTF-8"]

    @allure.title("Endpoint 6 response time acceptable")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("performance")
    def test_endpoint_6_response_time(self, base_url, headers):
        """Verify response time < 5 seconds"""
        with allure.step("Send GET request"):
            response = requests.get(
                f"{base_url}{TEST_ENDPOINT_6}",
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Verify response time"):
            response_time = response.elapsed.total_seconds()
            assert response_time < 5.0, \
                f"Response took {response_time:.3f}s, exceeds 5s limit"

    @allure.title("Endpoint 6 consistency - multiple calls")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("consistency")
    def test_endpoint_6_consistency_multiple_calls(self, base_url, headers):
        """Verify endpoint returns same status on 3 calls"""
        statuses = []

        with allure.step("Make 3 requests"):
            for i in range(3):
                response = requests.get(
                    f"{base_url}{TEST_ENDPOINT_6}",
                    headers=headers,
                    verify=SSL_VERIFY,
                    timeout=REQUEST_TIMEOUT
                )
                statuses.append(response.status_code)

        with allure.step("Verify all returned same status"):
            assert len(set(statuses)) == 1, f"Inconsistent: {statuses}"
