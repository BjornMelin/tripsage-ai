"""Tests for base service utilities."""

import os
from unittest.mock import patch

import pytest

from tripsage_core.services.external_apis.base_service import sanitize_response


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock environment variables to prevent Settings validation errors."""
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "testing",
            "DATABASE_URL": "https://test.supabase.co",
            "DATABASE_PUBLIC_KEY": "test-public-key",
            "DATABASE_SERVICE_KEY": "test-service-key",
            "DATABASE_JWT_SECRET": "test-jwt-secret",
            "OPENAI_API_KEY": "test-key",
        },
    ):
        yield


class TestSanitizeResponse:
    """Test sanitize_response function."""

    def test_sanitize_valid_json_dict(self):
        """Test sanitizing a valid JSON dict."""
        data = {"key": "value", "number": 42}
        result = sanitize_response(data)
        assert result == data

    def test_sanitize_valid_json_list(self):
        """Test sanitizing a valid JSON list."""
        data = [{"key": "value"}, {"number": 42}]
        result = sanitize_response(data)
        assert result == data

    def test_sanitize_invalid_json_with_nan(self):
        """Test that invalid JSON with NaN is sanitized to None."""
        data = {"value": float("nan")}
        result = sanitize_response(data)
        assert result == {"value": None}

    def test_sanitize_invalid_json_with_inf(self):
        """Test that invalid JSON with infinity is sanitized to None."""
        data = {"value": float("inf")}
        result = sanitize_response(data)
        assert result == {"value": None}

    def test_sanitize_invalid_json_with_neg_inf(self):
        """Test that invalid JSON with negative infinity is sanitized to None."""
        data = {"value": float("-inf")}
        result = sanitize_response(data)
        assert result == {"value": None}

    def test_sanitize_invalid_json_with_none_key(self):
        """Test that invalid JSON with None key is sanitized to string."""
        data = {None: "value"}
        result = sanitize_response(data)
        assert result == {"None": "value"}

    def test_sanitize_invalid_json_with_complex_key(self):
        """Test that invalid JSON with complex key is sanitized to string."""
        data = {(1, 2): "value"}
        result = sanitize_response(data)
        assert result == {"(1, 2)": "value"}

    def test_sanitize_invalid_json_with_set(self):
        """Test that invalid JSON with set is sanitized to string."""
        data = {"set": {1, 2, 3}}
        result = sanitize_response(data)
        assert isinstance(result, dict)
        assert "set" in result  # type: ignore[operator]
        assert isinstance(result["set"], str)  # type: ignore[index]
        # Sets are converted to string representation
        assert result["set"] == "{1, 2, 3}"  # type: ignore[index]

    def test_sanitize_invalid_json_with_bytes(self):
        """Test that invalid JSON with bytes is sanitized to string."""
        data = {"bytes": b"data"}
        result = sanitize_response(data)
        assert result == {"bytes": "b'data'"}  # type: ignore[comparison-overlap]

    def test_sanitize_invalid_json_with_datetime(self):
        """Test that invalid JSON with datetime is sanitized to string."""
        from datetime import datetime

        dt = datetime.now()
        data = {"datetime": dt}
        result = sanitize_response(data)
        assert isinstance(result, dict)
        assert "datetime" in result  # type: ignore[operator]
        assert isinstance(result["datetime"], str)  # type: ignore[index]

    def test_sanitize_nested_invalid_json(self):
        """Test that nested invalid JSON is sanitized."""
        data = {"nested": {"value": float("nan")}}
        result = sanitize_response(data)
        assert result == {"nested": {"value": None}}

    def test_sanitize_mixed_valid_invalid(self):
        """Test that mixed valid/invalid data is sanitized."""
        data = {"valid": "string", "invalid": float("nan")}
        result = sanitize_response(data)
        assert result == {"valid": "string", "invalid": None}

    def test_sanitize_malformed_json_string_raises_error(self):
        """Test that malformed JSON string raises ValueError."""
        with pytest.raises(ValueError):
            sanitize_response('{"invalid": json}')

    def test_sanitize_dangerous_prototype_keys(self):
        """Test that dangerous prototype-like keys are removed."""
        data = {
            "__proto__": {"admin": True},
            "constructor": "malicious",
            "prototype": "evil",
            "normal": "value",
        }
        result = sanitize_response(data)
        assert "__proto__" not in result  # type: ignore[operator]
        assert "constructor" not in result  # type: ignore[operator]
        assert "prototype" not in result  # type: ignore[operator]
        assert result == {"normal": "value"}

    def test_sanitize_empty_data(self):
        """Test sanitizing empty data."""
        data = {}
        result = sanitize_response(data)
        assert result == {}

    def test_sanitize_none_data(self):
        """Test sanitizing None data."""
        data = None
        result = sanitize_response(data)
        assert result is None

    def test_sanitize_nested_complex_structures(self):
        """Test sanitizing nested complex structures."""
        data = {
            "level1": {
                "level2": [
                    {"valid": "data"},
                    {"invalid": float("nan")},
                    {("complex", "key"): "value"},
                ]
            }
        }
        result = sanitize_response(data)
        assert result["level1"]["level2"][0] == {"valid": "data"}  # type: ignore[index]
        assert result["level1"]["level2"][1] == {"invalid": None}  # type: ignore[index]
        assert result["level1"]["level2"][2] == {"('complex', 'key')": "value"}  # type: ignore[index]
