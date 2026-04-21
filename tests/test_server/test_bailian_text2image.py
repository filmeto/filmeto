"""Integration-only Bailian text2image check.

This file stays in the repository for manual verification, but default unit
runs should not perform real network/API integration calls.
"""

import pytest


pytestmark = pytest.mark.skip(
    reason="integration test requiring real Bailian credentials and network"
)