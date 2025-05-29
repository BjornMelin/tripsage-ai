"""Simple test for the centralized exception system."""

# Now import our exceptions
from tripsage_core.exceptions import (
    CoreAuthenticationError,
    CoreTripSageError,
    ErrorDetails,
    format_exception,
)


def test_core_exception_basic():
    """Basic test for CoreTripSageError."""
    exc = CoreTripSageError("Test error", "TEST_ERROR")
    assert exc.message == "Test error"
    assert exc.code == "TEST_ERROR"
    assert exc.status_code == 500


def test_error_details_basic():
    """Basic test for ErrorDetails."""
    details = ErrorDetails(service="test-service")
    assert details.service == "test-service"
    assert details.operation is None


def test_authentication_error():
    """Test CoreAuthenticationError."""
    exc = CoreAuthenticationError()
    assert exc.message == "Authentication failed"
    assert exc.code == "AUTHENTICATION_ERROR"
    assert exc.status_code == 401


def test_format_exception():
    """Test format_exception utility."""
    exc = CoreTripSageError("Test error", "TEST_ERROR")
    result = format_exception(exc)

    assert result["error"] == "CoreTripSageError"
    assert result["message"] == "Test error"
    assert result["code"] == "TEST_ERROR"
    assert result["status_code"] == 500


if __name__ == "__main__":
    # Run tests directly
    test_core_exception_basic()
    test_error_details_basic()
    test_authentication_error()
    test_format_exception()
    print("All simple tests passed!")
