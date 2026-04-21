import os
import pytest


def pytest_collection_modifyitems(config, items):
    for item in items:
        item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def integration_env_ready():
    """Central gate for integration suite runtime requirements."""
    return os.environ.get("RUN_INTEGRATION_TESTS", "0") == "1"
