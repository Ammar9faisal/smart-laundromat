import httpx
import pytest

from app.errors import db_error
from tests.conftest import api_error


@pytest.mark.parametrize(
    ("code", "status"),
    [
        ("28000", 401),
        ("42501", 403),
        ("P0002", 404),
        ("22023", 422),
        ("LM001", 422),
        ("23P01", 409),
        ("LM002", 409),
        ("23505", 409),
    ],
)
def test_known_database_errors_map_to_http_status(code, status):
    error = db_error(api_error(code, "Readable message"), "Fallback")

    assert error.status_code == status
    assert error.detail == "Readable message"


def test_unknown_database_error_is_500_without_internal_details():
    error = db_error(api_error("XX000", "internal: relation foo"), "Failed to do it")

    assert error.status_code == 500
    assert error.detail == "Failed to do it"


def test_network_failure_is_503():
    error = db_error(httpx.ConnectError("connection refused"), "Failed to do it")

    assert error.status_code == 503
    assert error.detail == "Failed to do it: database unavailable"
