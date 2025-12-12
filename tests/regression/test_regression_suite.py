import pytest


@pytest.mark.parametrize("endpoint, golden_path")
def test_endpoint_regression(endpoint_schema, endpoint, golden_path):
    """Ensure endpoint responses haven't changed unexpectedly (parametrized)."""
    pass