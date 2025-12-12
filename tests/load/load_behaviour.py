"""
run this file with locust to perform load testing on multiple API endpoints.
Usage:
locust -f tests/load/load_behaviour.py

Open browser at http://localhost:8089 to access the Locust UI

locust -f  tests/load/load_behaviour.py --users 100 --spawn-rate 10 --run-time 5m --headless
"""
__test__ = False
import os
from locust import HttpUser, task, between
from constants import (
    HTTP_OK,
    HTTP_INTERNAL_ERROR,
    HTTP_SERVICE_UNAVAILABLE,
    AUTH_GENERATE_ENDPOINT,
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
    REQUEST_TIMEOUT
)

# Load from environment
BASE_URL = os.getenv("BASE_URL", "https://qa-home-assignment.magmadevs.com")
INITIAL_REFRESH_TOKEN = os.getenv("INITIAL_REFRESH_TOKEN", "initial_refresh_token_2024_qa_evaluation")


class EndpointUser(HttpUser):
    host = BASE_URL
    wait_time = between(0.5, 1)

    def on_start(self):
        # Get token once
        with self.client.post(
            AUTH_GENERATE_ENDPOINT,
            json={"refresh_token": INITIAL_REFRESH_TOKEN},
            catch_response=True
        ) as response:

            if response.status_code == HTTP_OK:
                self.token = response.json()["access_token"]
                response.success()
            else:
                response.failure(f"Auth failed with status {response.status_code}")
                self.token = None

    @task(6)
    def test_endpoint_1(self):
        if self.token:
            with self.client.get(
                TEST_ENDPOINT_1,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=REQUEST_TIMEOUT,
                catch_response=True
            ) as response:
                if response.status_code == HTTP_OK:
                    response.success()
                else:
                    response.failure(f"Status {response.status_code}")

    @task(5)
    def test_endpoint_2(self):
        if self.token:
            with self.client.get(
                TEST_ENDPOINT_2,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=REQUEST_TIMEOUT,
                catch_response=True
            ) as response:
                if response.status_code == HTTP_OK:
                    response.success()
                else:
                    response.failure(f"Status {response.status_code}")

    @task(4)
    def test_endpoint_3(self):
        if self.token:
            with self.client.get(
                TEST_ENDPOINT_3,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=REQUEST_TIMEOUT,
                catch_response=True
            ) as response:
                if response.status_code == HTTP_OK:
                    response.success()
                else:
                    response.failure(f"Status {response.status_code}")

    @task(3)
    def test_endpoint_4(self):
        if self.token:
            with self.client.get(
                TEST_ENDPOINT_4,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=REQUEST_TIMEOUT,
                catch_response=True
            ) as response:
                if response.status_code == HTTP_OK:
                    response.success()
                else:
                    response.failure(f"Status {response.status_code}")

    @task(2)
    def test_endpoint_5(self):
        if self.token:
            with self.client.get(
                TEST_ENDPOINT_5,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=REQUEST_TIMEOUT,
                catch_response=True
            ) as response:
                if response.status_code == HTTP_OK:
                    response.success()
                else:
                    response.failure(f"Status {response.status_code}")

    @task(1)
    def test_endpoint_6(self):
        if self.token:
            with self.client.get(
                TEST_ENDPOINT_6,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=REQUEST_TIMEOUT,
                catch_response=True
            ) as response:
                if response.status_code == HTTP_OK:
                    response.success()
                else:
                    response.failure(f"Status {response.status_code}")