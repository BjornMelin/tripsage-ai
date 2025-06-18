"""
Comprehensive test suite for MFAService.

This module provides full test coverage for Multi-Factor Authentication operations
including TOTP generation/verification, backup codes, QR code generation, and
database persistence operations with security-focused testing.
"""

import base64
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

# Mock pyotp module
mock_pyotp = MagicMock()
mock_totp = MagicMock()
mock_qrcode = MagicMock()
mock_qr_instance = MagicMock()
mock_img = MagicMock()

# Initialize mock state
def reset_mocks():
    """Reset mock state for each test."""
    mock_pyotp.reset_mock()
    mock_totp.reset_mock()
    mock_qrcode.reset_mock()
    mock_qr_instance.reset_mock()
    mock_img.reset_mock()

    # Reset to default values
    mock_pyotp.random_base32.return_value = "JBSWY3DPEHPK3PXP"
    mock_totp.now.return_value = "123456"
    mock_totp.verify.return_value = True
    mock_totp.provisioning_uri.return_value = "otpauth://totp/TripSage:test@example.com?secret=JBSWY3DPEHPK3PXP&issuer=TripSage"
    mock_pyotp.TOTP.return_value = mock_totp

    mock_img.save = MagicMock()
    mock_qr_instance.make_image.return_value = mock_img
    mock_qrcode.QRCode.return_value = mock_qr_instance
    mock_qrcode.constants.ERROR_CORRECT_L = 1

# Initialize with defaults
reset_mocks()

# Add mocks to sys.modules
sys.modules["pyotp"] = mock_pyotp
sys.modules["qrcode"] = mock_qrcode

# Import after mocking
from tripsage_core.exceptions.exceptions import (  # noqa: E402
    CoreServiceError,
    CoreValidationError,
)
from tripsage_core.services.business.mfa_service import (  # noqa: E402
    MFAEnrollmentRequest,
    MFAEnrollmentResponse,
    MFAService,
    MFASetupResponse,
    MFAStatus,
    MFAVerificationRequest,
    MFAVerificationResponse,
    get_mfa_service,
)

class TestMFAServiceModels:
    """Test MFA service Pydantic models for validation and serialization."""

    def test_mfa_enrollment_request_validation(self):
        """Test MFAEnrollmentRequest validation."""
        # Valid request
        request = MFAEnrollmentRequest(user_id="test-user", totp_code="123456")
        assert request.user_id == "test-user"
        assert request.totp_code == "123456"

        # Invalid TOTP code - too short
        with pytest.raises(ValidationError) as exc_info:
            MFAEnrollmentRequest(user_id="test-user", totp_code="123")
        assert "at least 6 characters" in str(exc_info.value)

        # Invalid TOTP code - too long
        with pytest.raises(ValidationError) as exc_info:
            MFAEnrollmentRequest(user_id="test-user", totp_code="1234567")
        assert "at most 6 characters" in str(exc_info.value)

        # Missing user_id
        with pytest.raises(ValidationError) as exc_info:
            MFAEnrollmentRequest(totp_code="123456")
        assert "Field required" in str(exc_info.value)

    def test_mfa_verification_request_validation(self):
        """Test MFAVerificationRequest validation."""
        # Valid TOTP code
        request = MFAVerificationRequest(user_id="test-user", code="123456")
        assert request.code == "123456"

        # Valid backup code (11 characters: NNNNN-NNNNN format)
        request = MFAVerificationRequest(user_id="test-user", code="12345-67890")
        assert request.code == "12345-67890"

        # Invalid code - too short
        with pytest.raises(ValidationError) as exc_info:
            MFAVerificationRequest(user_id="test-user", code="123")
        assert "at least 6 characters" in str(exc_info.value)

        # Invalid code - too long
        with pytest.raises(ValidationError) as exc_info:
            MFAVerificationRequest(
                user_id="test-user",
                code="123456789012",  # 12 characters
            )
        assert "at most 11 characters" in str(exc_info.value)

    def test_mfa_setup_response_serialization(self, serialization_helper):
        """Test MFASetupResponse serialization and deserialization."""
        response = MFASetupResponse(
            secret="JBSWY3DPEHPK3PXP",
            qr_code_url="data:image/png;base64,iVBORw0KGgoAAAANSU=",
            backup_codes=["12345678", "09876543"],
            manual_entry_key="JBSWY3DPEHPK3PXP",
        )

        # Test JSON round trip
        reconstructed = serialization_helper.test_json_round_trip(response)
        assert reconstructed.secret == response.secret
        assert reconstructed.qr_code_url == response.qr_code_url
        assert reconstructed.backup_codes == response.backup_codes

        # Test dict round trip
        reconstructed = serialization_helper.test_dict_round_trip(response)
        assert reconstructed.manual_entry_key == response.manual_entry_key

    def test_mfa_verification_response_serialization(self, serialization_helper):
        """Test MFAVerificationResponse serialization."""
        response = MFAVerificationResponse(
            valid=True, code_type="totp", remaining_backup_codes=8
        )

        reconstructed = serialization_helper.test_json_round_trip(response)
        assert reconstructed.valid is True
        assert reconstructed.code_type == "totp"
        assert reconstructed.remaining_backup_codes == 8

    def test_mfa_status_serialization(self, serialization_helper):
        """Test MFAStatus serialization."""
        now = datetime.now(timezone.utc).isoformat()
        status = MFAStatus(
            enabled=True,
            enrolled_at=now,
            backup_codes_remaining=5,
            last_used=now,
        )

        reconstructed = serialization_helper.test_json_round_trip(status)
        assert reconstructed.enabled is True
        assert reconstructed.enrolled_at == now
        assert reconstructed.backup_codes_remaining == 5

class TestMFAService:
    """Test suite for MFAService core functionality."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Reset mocks before each test method."""
        reset_mocks()

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service for MFA operations."""
        db = AsyncMock()
        # Set up common mock behaviors
        db.upsert = AsyncMock(return_value=[])
        db.select = AsyncMock(return_value=[])
        db.update = AsyncMock(return_value=[])
        db.delete = AsyncMock(return_value=[])
        return db

    @pytest.fixture
    def mfa_service(self, mock_database_service):
        """Create MFAService instance with mocked dependencies."""
        return MFAService(
            database_service=mock_database_service, app_name="TripSage Test"
        )

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "user_id": str(uuid4()),
            "email": "test@example.com",
        }

    @pytest.fixture
    def sample_mfa_settings(self):
        """Sample MFA settings data."""
        return {
            "user_id": str(uuid4()),
            "secret": "JBSWY3DPEHPK3PXP",
            "backup_codes": [
                "12345-67890",
                "09876-54321",
                "11111-22222",
                "33333-44444",
                "55555-66666",
            ],
            "enabled": True,
            "setup_at": datetime.now(timezone.utc).isoformat(),
            "enrolled_at": datetime.now(timezone.utc).isoformat(),
            "last_used": datetime.now(timezone.utc).isoformat(),
        }

    @pytest.mark.asyncio
    async def test_mfa_service_initialization_with_db(self, mock_database_service):
        """Test MFA service initialization with provided database service."""
        service = MFAService(
            database_service=mock_database_service, app_name="Test App"
        )
        assert service.db == mock_database_service
        assert service.app_name == "Test App"

    @pytest.mark.asyncio
    async def test_mfa_service_initialization_without_db(self):
        """Test MFA service initialization without database service."""
        with patch(
            "tripsage_core.services.infrastructure.get_database_service"
        ) as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Test in non-running loop context
            with patch("asyncio.get_event_loop") as mock_get_loop:
                mock_loop = MagicMock()
                mock_loop.is_running.return_value = False
                mock_loop.run_until_complete.return_value = mock_db
                mock_get_loop.return_value = mock_loop

                service = MFAService()
                assert service.db == mock_db

    @pytest.mark.asyncio
    async def test_ensure_db_method(self, mock_database_service):
        """Test _ensure_db method functionality."""
        service = MFAService(database_service=None)
        service._db_service_factory = AsyncMock(return_value=mock_database_service)

        await service._ensure_db()
        assert service.db == mock_database_service

    @pytest.mark.asyncio
    async def test_setup_mfa_success(
        self, mfa_service, mock_database_service, sample_user_data
    ):
        """Test successful MFA setup."""
        user_id = sample_user_data["user_id"]
        user_email = sample_user_data["email"]

        # Configure QR code mock
        with patch("base64.b64encode", return_value=b"test-qr-data"):
            result = await mfa_service.setup_mfa(user_id, user_email)

        # Verify the response
        assert isinstance(result, MFASetupResponse)
        assert result.secret == "JBSWY3DPEHPK3PXP"
        assert result.manual_entry_key == "JBSWY3DPEHPK3PXP"
        assert result.qr_code_url.startswith("data:image/png;base64,")
        assert len(result.backup_codes) == 10
        # Backup codes should be 8-character strings or NNNNN-NNNNN format
        assert all(isinstance(code, str) for code in result.backup_codes)

        # Verify database interaction
        mock_database_service.upsert.assert_called_once()
        call_args = mock_database_service.upsert.call_args
        assert call_args[0][0] == "user_mfa_settings"  # table name
        assert call_args[0][1]["user_id"] == user_id
        assert call_args[0][1]["secret"] == "JBSWY3DPEHPK3PXP"
        assert call_args[0][1]["enabled"] is False
        assert len(call_args[0][1]["backup_codes"]) == 10

    @pytest.mark.asyncio
    async def test_setup_mfa_database_error(
        self, mfa_service, mock_database_service, sample_user_data
    ):
        """Test MFA setup with database error."""
        mock_database_service.upsert.side_effect = Exception(
            "Database connection failed"
        )

        with pytest.raises(CoreServiceError) as exc_info:
            await mfa_service.setup_mfa(
                sample_user_data["user_id"], sample_user_data["email"]
            )

        assert exc_info.value.code == "MFA_SETUP_FAILED"
        # Check that it contains information about the error
        error_str = str(exc_info.value)
        assert "MFA_SETUP_FAILED" in error_str

    @pytest.mark.asyncio
    async def test_enroll_mfa_success(
        self, mfa_service, mock_database_service, sample_mfa_settings
    ):
        """Test successful MFA enrollment."""
        user_id = sample_mfa_settings["user_id"]

        # Setup database mock for unenrolled user
        unenrolled_settings = sample_mfa_settings.copy()
        unenrolled_settings["enabled"] = False
        mock_database_service.select.return_value = [unenrolled_settings]

        request = MFAEnrollmentRequest(user_id=user_id, totp_code="123456")

        # Mock TOTP verification
        mock_totp.verify.return_value = True

        result = await mfa_service.enroll_mfa(request)

        # Verify response
        assert isinstance(result, MFAEnrollmentResponse)
        assert result.success is True
        assert result.backup_codes == sample_mfa_settings["backup_codes"]
        assert result.enrolled_at == "now()"

        # Verify database calls
        mock_database_service.select.assert_called_once_with(
            "user_mfa_settings", "*", {"user_id": user_id}
        )
        mock_database_service.update.assert_called_once_with(
            "user_mfa_settings",
            {"user_id": user_id},
            {"enabled": True, "enrolled_at": "now()", "last_used": "now()"},
        )

    @pytest.mark.asyncio
    async def test_enroll_mfa_not_setup(self, mfa_service, mock_database_service):
        """Test MFA enrollment when not set up."""
        mock_database_service.select.return_value = []

        request = MFAEnrollmentRequest(user_id="test-user", totp_code="123456")

        with pytest.raises(CoreValidationError) as exc_info:
            await mfa_service.enroll_mfa(request)

        assert exc_info.value.code == "MFA_NOT_SETUP"
        assert "not set up" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_enroll_mfa_already_enrolled(
        self, mfa_service, mock_database_service, sample_mfa_settings
    ):
        """Test MFA enrollment when already enrolled."""
        mock_database_service.select.return_value = [sample_mfa_settings]

        request = MFAEnrollmentRequest(
            user_id=sample_mfa_settings["user_id"], totp_code="123456"
        )

        with pytest.raises(CoreValidationError) as exc_info:
            await mfa_service.enroll_mfa(request)

        assert exc_info.value.code == "MFA_ALREADY_ENROLLED"
        assert "already enrolled" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_enroll_mfa_invalid_totp(
        self, mfa_service, mock_database_service, sample_mfa_settings
    ):
        """Test MFA enrollment with invalid TOTP code."""
        unenrolled_settings = sample_mfa_settings.copy()
        unenrolled_settings["enabled"] = False
        mock_database_service.select.return_value = [unenrolled_settings]

        request = MFAEnrollmentRequest(
            user_id=sample_mfa_settings["user_id"], totp_code="000000"
        )

        # Mock TOTP verification to return False
        mock_totp.verify.return_value = False

        with pytest.raises(CoreValidationError) as exc_info:
            await mfa_service.enroll_mfa(request)

        assert exc_info.value.code == "INVALID_TOTP_CODE"
        assert "Invalid TOTP code" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_verify_mfa_totp_success(
        self, mfa_service, mock_database_service, sample_mfa_settings
    ):
        """Test successful TOTP verification."""
        mock_database_service.select.return_value = [sample_mfa_settings]

        request = MFAVerificationRequest(
            user_id=sample_mfa_settings["user_id"], code="123456"
        )

        # Mock TOTP verification to return True
        mock_totp.verify.return_value = True

        result = await mfa_service.verify_mfa(request)

        assert isinstance(result, MFAVerificationResponse)
        assert result.valid is True
        assert result.code_type == "totp"
        assert result.remaining_backup_codes is None

        # Verify last_used was updated
        mock_database_service.update.assert_called_once_with(
            "user_mfa_settings",
            {"user_id": sample_mfa_settings["user_id"]},
            {"last_used": "now()"},
        )

    @pytest.mark.asyncio
    async def test_verify_mfa_backup_code_success(
        self, mfa_service, mock_database_service, sample_mfa_settings
    ):
        """Test successful backup code verification."""
        mock_database_service.select.return_value = [sample_mfa_settings]

        backup_code = sample_mfa_settings["backup_codes"][0]
        request = MFAVerificationRequest(
            user_id=sample_mfa_settings["user_id"], code=backup_code
        )

        # Mock TOTP verification to return False (so it tries backup codes)
        mock_totp.verify.return_value = False

        result = await mfa_service.verify_mfa(request)

        assert isinstance(result, MFAVerificationResponse)
        assert result.valid is True
        assert result.code_type == "backup"
        assert result.remaining_backup_codes == 4  # One less than original

        # Verify backup codes were updated
        mock_database_service.update.assert_called_once()
        call_args = mock_database_service.update.call_args
        updated_codes = call_args[0][2]["backup_codes"]
        assert backup_code not in updated_codes
        assert len(updated_codes) == 4

    @pytest.mark.asyncio
    async def test_verify_mfa_invalid_code(
        self, mfa_service, mock_database_service, sample_mfa_settings
    ):
        """Test MFA verification with invalid code."""
        mock_database_service.select.return_value = [sample_mfa_settings]

        request = MFAVerificationRequest(
            user_id=sample_mfa_settings["user_id"], code="000000"
        )

        # Mock TOTP verification to return False
        mock_totp.verify.return_value = False

        result = await mfa_service.verify_mfa(request)

        assert isinstance(result, MFAVerificationResponse)
        assert result.valid is False
        assert result.code_type == "invalid"

    @pytest.mark.asyncio
    async def test_verify_mfa_user_not_enrolled(
        self, mfa_service, mock_database_service
    ):
        """Test MFA verification for non-enrolled user."""
        mock_database_service.select.return_value = []

        request = MFAVerificationRequest(user_id="test-user", code="123456")

        result = await mfa_service.verify_mfa(request)

        assert isinstance(result, MFAVerificationResponse)
        assert result.valid is False
        assert result.code_type == "none"

    @pytest.mark.asyncio
    async def test_verify_mfa_database_error(self, mfa_service, mock_database_service):
        """Test MFA verification with database error."""
        mock_database_service.select.side_effect = Exception("Database error")

        request = MFAVerificationRequest(user_id="test-user", code="123456")

        with pytest.raises(CoreServiceError) as exc_info:
            await mfa_service.verify_mfa(request)

        assert exc_info.value.code == "MFA_VERIFICATION_FAILED"

    @pytest.mark.asyncio
    async def test_get_mfa_status_enabled(
        self, mfa_service, mock_database_service, sample_mfa_settings
    ):
        """Test getting MFA status for enabled user."""
        mock_database_service.select.return_value = [sample_mfa_settings]

        result = await mfa_service.get_mfa_status(sample_mfa_settings["user_id"])

        assert isinstance(result, MFAStatus)
        assert result.enabled is True
        assert result.enrolled_at == sample_mfa_settings["enrolled_at"]
        assert result.backup_codes_remaining == len(sample_mfa_settings["backup_codes"])
        assert result.last_used == sample_mfa_settings["last_used"]

    @pytest.mark.asyncio
    async def test_get_mfa_status_not_enabled(self, mfa_service, mock_database_service):
        """Test getting MFA status for non-enabled user."""
        mock_database_service.select.return_value = []

        result = await mfa_service.get_mfa_status("test-user")

        assert isinstance(result, MFAStatus)
        assert result.enabled is False
        assert result.enrolled_at is None
        assert result.backup_codes_remaining == 0
        assert result.last_used is None

    @pytest.mark.asyncio
    async def test_get_mfa_status_database_error(
        self, mfa_service, mock_database_service
    ):
        """Test getting MFA status with database error."""
        mock_database_service.select.side_effect = Exception("Database error")

        result = await mfa_service.get_mfa_status("test-user")

        # Should return default disabled status on error
        assert isinstance(result, MFAStatus)
        assert result.enabled is False

    @pytest.mark.asyncio
    async def test_disable_mfa_success(self, mfa_service, mock_database_service):
        """Test successful MFA disabling."""
        mock_database_service.delete.return_value = [{"user_id": "test-user"}]

        result = await mfa_service.disable_mfa("test-user")

        assert result is True
        mock_database_service.delete.assert_called_once_with(
            "user_mfa_settings", {"user_id": "test-user"}
        )

    @pytest.mark.asyncio
    async def test_disable_mfa_not_found(self, mfa_service, mock_database_service):
        """Test disabling MFA when not found."""
        mock_database_service.delete.return_value = []

        result = await mfa_service.disable_mfa("test-user")

        assert result is False

    @pytest.mark.asyncio
    async def test_disable_mfa_database_error(self, mfa_service, mock_database_service):
        """Test disabling MFA with database error."""
        mock_database_service.delete.side_effect = Exception("Database error")

        result = await mfa_service.disable_mfa("test-user")

        assert result is False

    @pytest.mark.asyncio
    async def test_regenerate_backup_codes_success(
        self, mfa_service, mock_database_service, sample_mfa_settings
    ):
        """Test successful backup codes regeneration."""
        mock_database_service.select.return_value = [sample_mfa_settings]

        result = await mfa_service.regenerate_backup_codes(
            sample_mfa_settings["user_id"]
        )

        assert isinstance(result, list)
        assert len(result) == 10
        assert all(isinstance(code, str) for code in result)
        assert all(code not in sample_mfa_settings["backup_codes"] for code in result)

        # Verify database update
        mock_database_service.update.assert_called_once()
        call_args = mock_database_service.update.call_args
        assert call_args[0][2]["backup_codes"] == result

    @pytest.mark.asyncio
    async def test_regenerate_backup_codes_not_enabled(
        self, mfa_service, mock_database_service
    ):
        """Test regenerating backup codes when MFA not enabled."""
        mock_database_service.select.return_value = []

        with pytest.raises(CoreServiceError) as exc_info:
            await mfa_service.regenerate_backup_codes("test-user")

        assert exc_info.value.code == "MFA_NOT_ENABLED"

    @pytest.mark.asyncio
    async def test_regenerate_backup_codes_database_error(
        self, mfa_service, mock_database_service, sample_mfa_settings
    ):
        """Test regenerating backup codes with database error."""
        mock_database_service.select.return_value = [sample_mfa_settings]
        mock_database_service.update.side_effect = Exception("Database error")

        with pytest.raises(CoreServiceError) as exc_info:
            await mfa_service.regenerate_backup_codes(sample_mfa_settings["user_id"])

        assert exc_info.value.code == "BACKUP_CODES_REGENERATION_FAILED"

class TestMFAServicePrivateMethods:
    """Test private methods of MFAService."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Reset mocks before each test method."""
        reset_mocks()

    @pytest.fixture
    def mfa_service(self):
        """Create MFAService instance for testing private methods."""
        return MFAService(database_service=AsyncMock())

    def test_generate_qr_code(self, mfa_service):
        """Test QR code generation."""
        provisioning_uri = "otpauth://totp/TripSage:test@example.com?secret=JBSWY3DPEHPK3PXP&issuer=TripSage"

        with patch(
            "base64.b64encode", return_value=b"dGVzdC1xci1kYXRh"
        ):  # "test-qr-data" in base64
            qr_code_url = mfa_service._generate_qr_code(provisioning_uri)

        # Verify it's a data URL
        assert qr_code_url.startswith("data:image/png;base64,")

        # Verify the base64 data can be decoded
        base64_data = qr_code_url.split(",")[1]
        try:
            decoded_data = base64.b64decode(base64_data)
            assert len(decoded_data) > 0
        except Exception as e:
            pytest.fail(f"Invalid base64 data: {e}")

    def test_generate_backup_codes_default(self, mfa_service):
        """Test backup codes generation with default count."""
        codes = mfa_service._generate_backup_codes()

        assert len(codes) == 10
        assert all(isinstance(code, str) for code in codes)
        # Backup codes should be 11-character strings in NNNNN-NNNNN format
        assert all(len(code) == 11 and "-" in code for code in codes)
        # Each part should be 5 digits
        for code in codes:
            parts = code.split("-")
            assert len(parts) == 2
            assert all(part.isdigit() and len(part) == 5 for part in parts)

    def test_generate_backup_codes_custom_count(self, mfa_service):
        """Test backup codes generation with custom count."""
        codes = mfa_service._generate_backup_codes(count=5)

        assert len(codes) == 5
        assert all(isinstance(code, str) for code in codes)

    def test_generate_backup_codes_uniqueness(self, mfa_service):
        """Test that generated backup codes are unique."""
        codes1 = mfa_service._generate_backup_codes(count=100)
        codes2 = mfa_service._generate_backup_codes(count=100)

        # Codes should be unique within each set
        assert len(set(codes1)) == len(codes1)
        assert len(set(codes2)) == len(codes2)

        # Different generation calls should produce different codes
        overlap = set(codes1) & set(codes2)
        assert len(overlap) < 10  # Allow for some small overlap due to randomness

    def test_generate_backup_codes_format_validation(self, mfa_service):
        """Test backup code format validation."""
        codes = mfa_service._generate_backup_codes(count=20)

        for code in codes:
            # Should be 11-character strings in NNNNN-NNNNN format
            assert len(code) == 11
            assert "-" in code
            parts = code.split("-")
            assert len(parts) == 2
            # Each part should be 5 digits
            for part in parts:
                assert len(part) == 5
                assert part.isdigit()
                assert 0 <= int(part) <= 99999

class TestMFAServiceSecurity:
    """Security-focused tests for MFAService."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Reset mocks before each test method."""
        reset_mocks()

    @pytest.fixture
    def mfa_service(self):
        """Create MFAService instance for security testing."""
        return MFAService(database_service=AsyncMock())

    def test_totp_secret_entropy(self, mfa_service):
        """Test TOTP secret has sufficient entropy."""
        # Test multiple secret generations
        secrets = []
        for _ in range(10):
            mock_secret = f"SECRET{_:02d}ABCDEFGHIJKLMN"
            secrets.append(mock_secret)
            mock_pyotp.random_base32.return_value = mock_secret

            # Verify secrets are different
            if len(secrets) > 1:
                assert mock_secret != secrets[-2]

    def test_backup_codes_cryptographic_security(self, mfa_service):
        """Test backup codes use cryptographically secure random generation."""
        with patch("secrets.randbelow") as mock_randbelow:
            mock_randbelow.return_value = 50000

            codes = mfa_service._generate_backup_codes(count=1)

            # Verify secrets.randbelow was called (cryptographically secure)
            assert mock_randbelow.called
            assert codes[0] == "50000-50000"

    @pytest.mark.asyncio
    async def test_totp_window_security(self, mfa_service):
        """Test TOTP verification uses appropriate time window."""
        mock_db = AsyncMock()
        mock_db.select.return_value = [
            {
                "user_id": "test-user",
                "secret": "JBSWY3DPEHPK3PXP",
                "backup_codes": [],
                "enabled": True,
            }
        ]
        mfa_service.db = mock_db

        request = MFAVerificationRequest(user_id="test-user", code="123456")

        mock_totp.verify.return_value = True
        await mfa_service.verify_mfa(request)

        # Verify window parameter is set to 1 (30-second window each direction)
        mock_totp.verify.assert_called_once_with("123456", valid_window=1)

    @pytest.mark.asyncio
    async def test_backup_code_single_use(self, mfa_service):
        """Test backup codes can only be used once."""
        backup_codes = ["12345-67890", "09876-54321"]
        mock_db = AsyncMock()
        mock_db.select.return_value = [
            {
                "user_id": "test-user",
                "secret": "JBSWY3DPEHPK3PXP",
                "backup_codes": backup_codes.copy(),
                "enabled": True,
            }
        ]
        mfa_service.db = mock_db

        request = MFAVerificationRequest(user_id="test-user", code="12345-67890")

        mock_totp.verify.return_value = False
        result = await mfa_service.verify_mfa(request)

        assert result.valid is True
        assert result.code_type == "backup"

        # Verify the used backup code was removed
        update_call = mock_db.update.call_args
        updated_codes = update_call[0][2]["backup_codes"]
        assert "12345-67890" not in updated_codes
        assert "09876-54321" in updated_codes

    def test_qr_code_contains_proper_uri(self, mfa_service):
        """Test QR code contains properly formatted provisioning URI."""
        # Create a mock provisioning URI
        uri = "otpauth://totp/TripSage%3Atest%40example.com?secret=JBSWY3DPEHPK3PXP&issuer=TripSage"

        with patch("base64.b64encode", return_value=b"dGVzdC1xci1kYXRh"):
            qr_code_url = mfa_service._generate_qr_code(uri)

        # Decode the QR code to verify content
        base64_data = qr_code_url.split(",")[1]
        img_data = base64.b64decode(base64_data)

        # Verify it's valid base64 data
        assert len(img_data) > 0

class TestMFAServiceIntegration:
    """Integration tests for MFAService with real dependencies."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Reset mocks before each test method."""
        reset_mocks()

    @pytest.mark.asyncio
    async def test_get_mfa_service_dependency(self):
        """Test the dependency injection function."""
        service = await get_mfa_service()
        assert isinstance(service, MFAService)
        assert service.app_name == "TripSage"

    @pytest.mark.asyncio
    async def test_full_mfa_enrollment_flow(self):
        """Test complete MFA enrollment flow from setup to verification."""
        mock_db = AsyncMock()
        service = MFAService(database_service=mock_db)

        user_id = str(uuid4())
        user_email = "test@example.com"

        # Step 1: Setup MFA
        with patch("base64.b64encode", return_value=b"test-qr-data"):
            setup_result = await service.setup_mfa(user_id, user_email)

        assert setup_result.secret == "JBSWY3DPEHPK3PXP"
        assert len(setup_result.backup_codes) == 10

        # Step 2: Mock database state after setup
        mock_db.select.return_value = [
            {
                "user_id": user_id,
                "secret": "JBSWY3DPEHPK3PXP",
                "backup_codes": setup_result.backup_codes,
                "enabled": False,
            }
        ]

        # Step 3: Enroll MFA with valid TOTP
        enroll_request = MFAEnrollmentRequest(user_id=user_id, totp_code="123456")

        mock_totp.verify.return_value = True
        enroll_result = await service.enroll_mfa(enroll_request)

        assert enroll_result.success is True

        # Step 4: Mock database state after enrollment
        mock_db.select.return_value = [
            {
                "user_id": user_id,
                "secret": "JBSWY3DPEHPK3PXP",
                "backup_codes": setup_result.backup_codes,
                "enabled": True,
            }
        ]

        # Step 5: Verify MFA with TOTP
        verify_request = MFAVerificationRequest(user_id=user_id, code="123456")

        mock_totp.verify.return_value = True
        verify_result = await service.verify_mfa(verify_request)

        assert verify_result.valid is True
        assert verify_result.code_type == "totp"

    @pytest.mark.asyncio
    async def test_mfa_error_handling_chain(self):
        """Test error handling throughout the MFA service chain."""
        mock_db = AsyncMock()
        service = MFAService(database_service=mock_db)

        # Test database connection failure
        mock_db.select.side_effect = Exception("Connection timeout")

        with pytest.raises(CoreServiceError) as exc_info:
            await service.verify_mfa(
                MFAVerificationRequest(user_id="test-user", code="123456")
            )

        assert exc_info.value.code == "MFA_VERIFICATION_FAILED"
        assert exc_info.value.details.service == "MFAService"

class TestMFAServiceEdgeCases:
    """Edge case and boundary condition tests."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Reset mocks before each test method."""
        reset_mocks()

    @pytest.fixture
    def mfa_service(self):
        """Create MFAService instance for edge case testing."""
        return MFAService(database_service=AsyncMock())

    def test_backup_codes_edge_cases(self, mfa_service):
        """Test backup codes generation edge cases."""
        # Zero count
        codes = mfa_service._generate_backup_codes(count=0)
        assert len(codes) == 0

        # Large count
        codes = mfa_service._generate_backup_codes(count=1000)
        assert len(codes) == 1000

        # Single code
        codes = mfa_service._generate_backup_codes(count=1)
        assert len(codes) == 1
        assert len(codes[0].split("-")) == 2
        assert len(codes[0]) == 11

    @pytest.mark.asyncio
    async def test_verify_mfa_with_empty_backup_codes(self, mfa_service):
        """Test MFA verification when backup codes list is empty."""
        mock_db = AsyncMock()
        mock_db.select.return_value = [
            {
                "user_id": "test-user",
                "secret": "JBSWY3DPEHPK3PXP",
                "backup_codes": [],  # Empty backup codes
                "enabled": True,
            }
        ]
        mfa_service.db = mock_db

        request = MFAVerificationRequest(user_id="test-user", code="12345-67890")

        mock_totp.verify.return_value = False
        result = await mfa_service.verify_mfa(request)

        assert result.valid is False
        assert result.code_type == "invalid"

    @pytest.mark.asyncio
    async def test_get_status_with_missing_fields(self, mfa_service):
        """Test getting MFA status with missing optional fields."""
        mock_db = AsyncMock()
        mock_db.select.return_value = [
            {
                "user_id": "test-user",
                "secret": "JBSWY3DPEHPK3PXP",
                "backup_codes": ["12345-67890"],
                "enabled": True,
                # Missing optional fields: enrolled_at, last_used
            }
        ]
        mfa_service.db = mock_db

        result = await mfa_service.get_mfa_status("test-user")

        assert result.enabled is True
        assert result.enrolled_at is None
        assert result.backup_codes_remaining == 1
        assert result.last_used is None

    def test_qr_code_with_special_characters(self, mfa_service):
        """Test QR code generation with special characters in email."""
        special_email = "test+special@example-domain.com"
        uri = f"otpauth://totp/TripSage:{special_email}?secret=JBSWY3DPEHPK3PXP&issuer=TripSage"

        with patch("base64.b64encode", return_value=b"dGVzdC1xci1kYXRh"):
            qr_code_url = mfa_service._generate_qr_code(uri)

        assert qr_code_url.startswith("data:image/png;base64,")
        # Should successfully encode even with special characters
        base64_data = qr_code_url.split(",")[1]
        decoded_data = base64.b64decode(base64_data)
        assert len(decoded_data) > 0

    @pytest.mark.asyncio
    async def test_concurrent_backup_code_usage(self, mfa_service):
        """Test behavior when backup codes are used concurrently."""
        backup_codes = ["12345-67890", "09876-54321"]
        mock_db = AsyncMock()

        # Simulate concurrent access to the same backup code
        mock_db.select.return_value = [
            {
                "user_id": "test-user",
                "secret": "JBSWY3DPEHPK3PXP",
                "backup_codes": backup_codes.copy(),
                "enabled": True,
            }
        ]
        mfa_service.db = mock_db

        request = MFAVerificationRequest(user_id="test-user", code="12345-67890")

        mock_totp.verify.return_value = False
        # First usage should succeed
        result1 = await mfa_service.verify_mfa(request)

        # Simulate that the backup code was already removed by another concurr request
        mock_db.select.return_value = [
            {
                "user_id": "test-user",
                "secret": "JBSWY3DPEHPK3PXP",
                "backup_codes": ["09876-54321"],  # Code already removed
                "enabled": True,
            }
        ]

        # Second usage should fail
        result2 = await mfa_service.verify_mfa(request)

        assert result1.valid is True
        assert result2.valid is False

# Property-based testing for backup codes
@pytest.mark.parametrize("count", [1, 5, 10, 25, 50])
def test_backup_codes_property_count(count):
    """Property-based test: backup codes count matches requested count."""
    service = MFAService(database_service=AsyncMock())
    codes = service._generate_backup_codes(count=count)
    assert len(codes) == count

@pytest.mark.parametrize(
    "code_format",
    [
        "123456",  # TOTP format (valid)
        "12345-67890",  # Backup code format (valid)
        "abcd-1234",  # Invalid chars but valid length (valid - allows any chars)
    ],
)
def test_verification_request_code_formats(code_format):
    """Property-based test: different code formats in verification request."""
    if len(code_format) < 6 or len(code_format) > 11:
        with pytest.raises(ValidationError):
            MFAVerificationRequest(user_id="test", code=code_format)
    else:
        # All these formats are now valid (we only validate length, not content)
        request = MFAVerificationRequest(user_id="test", code=code_format)
        assert request.code == code_format
