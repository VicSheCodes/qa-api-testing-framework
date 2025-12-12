import allure
import pytest
import requests
import os
from allure_commons.types import AttachmentType
from collections import defaultdict
from http import HTTPStatus
from dotenv import load_dotenv
from config.logger_config import get_test_logger, log_test_start, log_test_end
from constants import AUTH_GENERATE_ENDPOINT, HTTP_OK, AUTH_TIMEOUT, SCHEMA_DIR
from utils.schema_manager import SchemaManager

# loading environment variables from .env file
load_dotenv()

SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() == "true"

# Initialize logger
logger = get_test_logger()

# setup initial refresh token and base URL from.env
INITIAL_REFRESH_TOKEN = os.getenv("INITIAL_REFRESH_TOKEN")
BASE_URL = os.getenv("BASE_URL", "https://qa-home-assignment.magmadevs.com")

if not INITIAL_REFRESH_TOKEN:
    raise ValueError("INITIAL_REFRESH_TOKEN must be set in .env file")


# Global collector for endpoint discovery results
_endpoint_results = defaultdict(lambda: {
    "status_codes": [],
    "response_times": [],
    "test_count": 0,
    "passed": 0,
    "failed": 0
})


# Ptyest hooks

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture test results for logging
    The hook captures the outcome of each test phase (setup, call, teardown)
    and logs the test result accordingly.
    """
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        test_name = item.nodeid
        duration = report.duration

        # Allure metadata
        allure.dynamic.parameter("Test Name", test_name)
        allure.dynamic.parameter("Duration", f"{duration:.3f}s")

        if report.passed:
            log_test_end(test_name, "PASSED", duration)
            allure.dynamic.severity(allure.severity_level.NORMAL)
        elif report.failed:
            log_test_end(test_name, "FAILED", duration)
            allure.dynamic.severity(allure.severity_level.CRITICAL)

            # Attach failure logs to Allure
            if report.longrepr:
                allure.attach(
                    str(report.longreprtext),
                    name="Failure Details",
                    attachment_type=AttachmentType.TEXT
                )
                logger.error(f"Failure reason: {report.longreprtext}")
        elif report.skipped:
            log_test_end(test_name, "SKIPPED", duration)
            allure.dynamic.severity(allure.severity_level.TRIVIAL)


# Pytest fixtures


# @pytest.fixture(scope="session", autouse=True)
# def allure_environment(base_url):
#     """Add environment info to Allure report"""
#     import os
#     from pathlib import Path
#
#     allure_dir = Path("allure-results")
#     allure_dir.mkdir(exist_ok=True)
#
#     env_file = allure_dir / "environment.properties"
#     with open(env_file, 'w') as f:
#         f.write(f"Base.URL={base_url}\n")
#         f.write(f"Environment={'QA' if 'qa' in base_url else 'Production'}\n")
#         f.write(f"SSL.Verify={SSL_VERIFY}\n")
#         f.write(f"Python.Version={os.sys.version}\n")
#

@pytest.fixture(scope="session", autouse=True)
def setup_allure_environment(base_url):
    """Configure Allure environment metadata"""
    import os

    allure.dynamic.parameter("Base URL", base_url)
    allure.dynamic.parameter("Environment", "QA" if "qa" in base_url else "Production")
    allure.dynamic.parameter("SSL Verification", SSL_VERIFY)
    allure.dynamic.parameter("Python Version", os.sys.version)
@pytest.fixture(scope="session", autouse=True)
def log_session_start():
    """Log test session start and summary at end"""
    logger.info("=" * 80)
    logger.info("TEST SESSION STARTED")
    logger.info(f"Base URL: {BASE_URL}")
    logger.info("=" * 80)

    yield

    _print_endpoint_discovery_summary()


def _print_endpoint_discovery_summary():
    """Print comprehensive endpoint discovery summary with status codes"""
    if not _endpoint_results:
        logger.debug("No endpoint discovery tests executed in this session")
        return

    logger.info("\n" + "=" * 80)
    logger.info("ENDPOINT DISCOVERY SUMMARY")
    logger.info("=" * 80)
    sorted_endpoints = sorted(_endpoint_results.keys(),
                             key=lambda x: int(x.split('/')[-1]))

    successful_endpoints = []
    failed_endpoints = []

    for endpoint in sorted_endpoints:
        data = _endpoint_results[endpoint]

        # Determine if endpoint is "healthy" (has at least one 200 response)
        has_success = 200 in data["status_codes"]

        # Count status code occurrences
        status_distribution = {}
        for code in data["status_codes"]:
            status_distribution[code] = status_distribution.get(code, 0) + 1

        # Format status codes with names
        status_summary = []
        for code, count in sorted(status_distribution.items()):
            try:
                status_name = HTTPStatus(code).name
            except ValueError:
                status_name = "UNKNOWN"
            status_summary.append(f"{code} {status_name} ({count}x)")

        # Calculate average response time
        avg_time = sum(data["response_times"]) / len(data["response_times"]) if data["response_times"] else 0

        # Determine overall status
        if has_success and len(status_distribution) == 1 and 200 in status_distribution:
            status_icon = "✓"
            status_text = "OK"
            successful_endpoints.append(endpoint)
        elif has_success:
            status_icon = "⚠"
            status_text = "UNSTABLE"
            failed_endpoints.append(endpoint)
        else:
            status_icon = "✗"
            status_text = "FAILED"
            failed_endpoints.append(endpoint)

        logger.info(f"\n{status_icon} {endpoint}")
        logger.info(f"   Status: {status_text}")
        logger.info(f"   Tests: {data['test_count']} | Passed: {data['passed']} | Failed: {data['failed']}")
        logger.info(f"   Observed Status Codes: {', '.join(status_summary)}")
        logger.info(f"   Avg Response Time: {avg_time:.3f}s")

    logger.info("\n" + "-" * 80)
    logger.info(f"OVERALL RESULTS")
    logger.info("-" * 80)
    logger.info(f"✓ Stable Endpoints:   {len(successful_endpoints)}/6")
    logger.info(f"⚠ Unstable Endpoints: {len([e for e in failed_endpoints if _endpoint_results[e].get('status_codes') and 200 in _endpoint_results[e]['status_codes']])}/6")
    logger.info(f"✗ Failed Endpoints:   {len([e for e in failed_endpoints if _endpoint_results[e].get('status_codes') and 200 not in _endpoint_results[e]['status_codes']])}/6")

    total_tests = sum(data['test_count'] for data in _endpoint_results.values())
    total_passed = sum(data['passed'] for data in _endpoint_results.values())
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

    logger.info(f"\nTotal Tests: {total_tests} | Passed: {total_passed} | Success Rate: {success_rate:.1f}%")
    logger.info("=" * 80 + "\n")


@pytest.fixture(scope="function", autouse=True)
def log_test_info(request):
    """Automatically log test start"""
    test_name = request.node.nodeid
    params = getattr(request.node, "callspec", None)
    param_dict = params.params if params else None

    log_test_start(test_name, param_dict)

    yield


@pytest.fixture(scope="session")
def base_url():
    """Base URL for all API requests"""
    return BASE_URL


@pytest.fixture(scope="session")
def initial_refresh_token():
    """Initial refresh token for authentication"""
    return INITIAL_REFRESH_TOKEN


@pytest.fixture(scope="session")
def auth_token(base_url, initial_refresh_token):
    """Generate access token, session scope"""
    logger.info("Generating session access token...")
    endpoint = f"{base_url}{AUTH_GENERATE_ENDPOINT}"

    response = requests.post(
        endpoint,
        json={"refresh_token": initial_refresh_token},
        timeout=AUTH_TIMEOUT,
        verify=SSL_VERIFY  # ← ADD THIS FOR CHARLES
    )

    if response.status_code == HTTP_OK:
        logger.info("Session access token generated successfully")
    else:
        logger.error(f"Failed to generate token: {response.status_code}")
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def fresh_auth_token(base_url, initial_refresh_token):
    """Generate fresh access token for each test"""
    logger.debug("Generating fresh access token for test...")
    response = requests.post(
        f"{base_url}{AUTH_GENERATE_ENDPOINT}",
        json={"refresh_token": initial_refresh_token},
        timeout=AUTH_TIMEOUT,
        verify=False  # ← ADD THIS FOR CHARLES

    )
    if response.status_code != HTTP_OK:
        raise Exception(f"Failed to generate token: {response.status_code}")

    token_data = response.json()

    return token_data["access_token"]


@pytest.fixture
def headers(auth_token):
    """Authorization headers with bearer token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="session")
def schema_manager(base_url):
    """
    Session-scoped OpenAPI schema manager.
    Provides access to schema and endpoint details, to read/parse/validate schema in tests.
    :param base_url: Base URL of the API server
    :return: SchemaManager instance
    """
    manager = SchemaManager(base_url, SCHEMA_DIR)

    try:
        manager.download_schema()
        logger.info(" OpenAPI schema loaded successfully")
    except Exception as e:
        logger.warning(f" Could not load OpenAPI schema: {e}")

    return manager


@pytest.fixture(scope="session")
def openapi_schema(schema_manager):
    """Get full OpenAPI schema"""
    return schema_manager.get_schema()


@pytest.fixture
def endpoint_schema(schema_manager):
    """Factory fixture to get schema for specific endpoint"""
    def _get_endpoint_schema(path: str, method: str = "get"):
        return schema_manager.get_endpoint_schema(path, method)
    return _get_endpoint_schema