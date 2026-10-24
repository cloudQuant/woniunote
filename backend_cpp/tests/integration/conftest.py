"""Pytest fixtures for the isolated real-backend suite."""

import pytest

from iter21_support import login, register_user


@pytest.fixture
def credentials():
    return register_user()


@pytest.fixture
def user(credentials):
    return login(credentials)


def pytest_collection_modifyitems(items):
    # Fault injection runs after ordinary API contracts. The transport proxy
    # suite comes last, and the default rate-limit check is isolated in its own
    # runner scenario and still sorts last within that scenario.
    def order(item):
        transport = item.path.name == "test_iter21_transport_faults.py"
        rate = item.path.name == "test_z_rate_limit.py"
        fault = item.get_closest_marker("fault_injection") is not None
        return (rate, transport, fault)

    items.sort(key=order)
