import requests
import json
import yaml
from pathlib import Path
from config.logger_config import get_test_logger
from constants import (
    SCHEMA_DOWNLOAD_TIMEOUT,
    OPENAPI_YAML_ENDPOINT
)


logger = get_test_logger()


class SchemaManager:
    """Manage OpenAPI schema download and access"""

    def __init__(self, base_url: str, schema_dir: str = "data/schemas"):
        self.base_url = base_url
        self.schema_dir = Path(schema_dir)
        self.schema_dir.mkdir(parents=True, exist_ok=True)
        self.schema_file = self.schema_dir / "openapi_schema.json"

    def download_schema(self, force: bool = False) -> Path:
        """Download OpenAPI schema from server (YAML) and convert to JSON"""
        from conftest import SSL_VERIFY
        if self.schema_file.exists() and not force:
            # TODO: Verify schema freshness? force to redownload
            logger.info(f" OpenAPI schema already exists: {self.schema_file}")
            return self.schema_file

        logger.info(f" Downloading OpenAPI schema from {self.base_url}...")

        try:
            response = requests.get(
                f"{self.base_url}{OPENAPI_YAML_ENDPOINT}",
                timeout=SCHEMA_DOWNLOAD_TIMEOUT,
                verify=SSL_VERIFY,
            )
            response.raise_for_status()
            schema = yaml.safe_load(response.text)

            # Save as JSON
            with open(self.schema_file, 'w') as f:
                json.dump(schema, f, indent=2)

            logger.info(f" OpenAPI schema saved: {self.schema_file}")
            return self.schema_file

        except requests.exceptions.RequestException as e:
            logger.error(f" Failed to download OpenAPI schema: {e}")
            raise

    def get_schema(self) -> dict:
        """Load and return OpenAPI schema"""
        if not self.schema_file.exists():
            self.download_schema()

        with open(self.schema_file) as f:
            return json.load(f)

    def get_endpoint_schema(self, path: str, method: str = "get") -> dict:
        """Get schema for specific endpoint"""
        schema = self.get_schema()

        if path not in schema.get("paths", {}):
            raise ValueError(f"Endpoint {path} not found in schema")

        endpoint = schema["paths"][path]

        if method.lower() not in endpoint:
            raise ValueError(f"Method {method} not supported for {path}")

        return endpoint[method.lower()]

    def get_all_test_endpoints(self) -> list:
        """Extract all /api/test/* endpoints from schema"""
        schema = self.get_schema()
        test_endpoints = []

        for path in schema.get("paths", {}).keys():
            if path.startswith("/api/test/"):
                test_endpoints.append(path)

        return sorted(test_endpoints)