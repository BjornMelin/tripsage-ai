"""Tests for base service utilities."""

import pytest
from pydantic import ValidationError

from tripsage_core.services.external_apis.base_service import sanitize_response


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
        """Test that invalid JSON with NaN raises ValidationError."""
        data = {"value": float("nan")}
        with pytest.raises(ValidationError):
            sanitize_response(data)

    def test_sanitize_invalid_json_with_inf(self):
        """Test that invalid JSON with infinity raises ValidationError."""
        data = {"value": float("inf")}
        with pytest.raises(ValidationError):
            sanitize_response(data)

    def test_sanitize_invalid_json_with_neg_inf(self):
        """Test that invalid JSON with negative infinity raises ValidationError."""
        data = {"value": float("-inf")}
        with pytest.raises(ValidationError):
            sanitize_response(data)

    def test_sanitize_invalid_json_with_none_key(self):
        """Test that invalid JSON with None key raises ValidationError."""
        data = {None: "value"}
        with pytest.raises(ValidationError):
            sanitize_response(data)

    def test_sanitize_invalid_json_with_complex_key(self):
        """Test that invalid JSON with complex key raises ValidationError."""
        data = {(1, 2): "value"}
        with pytest.raises(ValidationError):
            sanitize_response(data)

    def test_sanitize_invalid_json_with_set(self):
        """Test that invalid JSON with set raises ValidationError."""
        data = {"set": {1, 2, 3}}
        with pytest.raises(ValidationError):
            sanitize_response(data)

    def test_sanitize_invalid_json_with_bytes(self):
        """Test that invalid JSON with bytes raises ValidationError."""
        data = {"bytes": b"data"}
        with pytest.raises(ValidationError):
            sanitize_response(data)

    def test_sanitize_invalid_json_with_datetime(self):
        """Test that invalid JSON with datetime raises ValidationError."""
        from datetime import datetime

        data = {"datetime": datetime.now()}
        with pytest.raises(ValidationError):
            sanitize_response(data)

    def test_sanitize_nested_invalid_json(self):
        """Test that nested invalid JSON raises ValidationError."""
        data = {"nested": {"value": float("nan")}}
        with pytest.raises(ValidationError):
            sanitize_response(data)

    def test_sanitize_mixed_valid_invalid(self):
        """Test that mixed valid/invalid data raises ValidationError."""
        data = {"valid": "string", "invalid": float("nan")}
        with pytest.raises(ValidationError):
            sanitize_response(data)
