"""
Pytest configuration and global test fixtures.
"""

import pytest
from backend.app.services.rate_limiter import reset_rate_limiter


@pytest.fixture(autouse=True)
def isolate_test_environment(request):
    """
    Ensure each test function runs with:
    1. Clean cookie state on TestClient, preventing state leakage between tests.
    2. Reset rate limiter state, preventing rate limit throttling from leaking into subsequent tests.
    """
    reset_rate_limiter()
    if "client" in request.fixturenames:
        client = request.getfixturevalue("client")
        client.cookies.clear()
        yield
        client.cookies.clear()
        reset_rate_limiter()
    else:
        yield
        reset_rate_limiter()
