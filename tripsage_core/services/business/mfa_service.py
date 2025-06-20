"""
Multi-Factor Authentication (MFA) Service for TripSage.

This service provides TOTP-based MFA functionality including:
- QR code generation for authenticator apps
- TOTP verification
- Backup codes generation and validation
- MFA enrollment and management
"""

import base64
import logging
import secrets
from io import BytesIO
from typing import List, Optional

import pyotp
import qrcode
from pydantic import Field

from tripsage_core.exceptions.exceptions import (
    CoreServiceError,
    CoreValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel

logger = logging.getLogger(__name__)


class MFAEnrollmentRequest(TripSageModel):
    """Request to enroll in MFA."""

    user_id: str = Field(..., description="User ID")
    totp_code: str = Field(
        ..., min_length=6, max_length=6, description="TOTP verification code"
    )


class MFAEnrollmentResponse(TripSageModel):
    """Response for MFA enrollment."""

    backup_codes: List[str] = Field(..., description="One-time backup codes")
    enrolled_at: str = Field(..., description="Enrollment timestamp")
    success: bool = Field(..., description="Whether enrollment was successful")


class MFASetupResponse(TripSageModel):
    """Response for MFA setup initiation."""

    secret: str = Field(..., description="TOTP secret key")
    qr_code_url: str = Field(..., description="QR code data URL")
    backup_codes: List[str] = Field(..., description="One-time backup codes")
    manual_entry_key: str = Field(..., description="Manual entry key for apps")


class MFAVerificationRequest(TripSageModel):
    """Request to verify MFA code."""

    user_id: str = Field(..., description="User ID")
    code: str = Field(
        ...,
        min_length=6,
        max_length=11,
        description="TOTP (6 chars) or backup code (11 chars)",
    )


class MFAVerificationResponse(TripSageModel):
    """Response for MFA verification."""

    valid: bool = Field(..., description="Whether the code is valid")
    code_type: str = Field(..., description="Type of code (totp, backup)")
    remaining_backup_codes: Optional[int] = Field(
        None, description="Remaining backup codes"
    )


class MFAStatus(TripSageModel):
    """MFA status for a user."""

    enabled: bool = Field(..., description="Whether MFA is enabled")
    enrolled_at: Optional[str] = Field(None, description="Enrollment timestamp")
    backup_codes_remaining: int = Field(
        default=0, description="Number of backup codes remaining"
    )
    last_used: Optional[str] = Field(None, description="Last successful verification")


class MFAService:
    """
    Multi-Factor Authentication service for TOTP and backup codes.

    This service handles:
    - TOTP secret generation and QR code creation
    - Code verification (TOTP and backup codes)
    - MFA enrollment and management
    - Backup code generation and tracking
    """

    def __init__(self, database_service=None, app_name: str = "TripSage"):
        """
        Initialize MFA service.

        Args:
            database_service: Database service for persistence
            app_name: Application name for TOTP generation
        """
        if database_service is None:
            import asyncio

            from tripsage_core.services.infrastructure import get_database_service

            # Get database service in async context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we'll need to handle this differently
                self.db = None
                self._db_service_factory = get_database_service
            else:
                self.db = loop.run_until_complete(get_database_service())
        else:
            self.db = database_service

        self.app_name = app_name

    async def _ensure_db(self):
        """Ensure database service is available."""
        if self.db is None and hasattr(self, "_db_service_factory"):
            self.db = await self._db_service_factory()

    async def setup_mfa(self, user_id: str, user_email: str) -> MFASetupResponse:
        """
        Set up MFA for a user (generate secret and QR code).

        Args:
            user_id: User ID
            user_email: User email for QR code label

        Returns:
            MFA setup response with secret and QR code

        Raises:
            CoreServiceError: If setup fails
        """
        try:
            await self._ensure_db()

            # Generate TOTP secret
            secret = pyotp.random_base32()

            # Create TOTP instance
            totp = pyotp.TOTP(secret)

            # Generate provisioning URI for QR code
            provisioning_uri = totp.provisioning_uri(
                name=user_email, issuer_name=self.app_name
            )

            # Generate QR code
            qr_code_url = self._generate_qr_code(provisioning_uri)

            # Generate backup codes
            backup_codes = self._generate_backup_codes()

            # Store MFA setup in database (not yet enabled)
            await self.db.upsert(
                "user_mfa_settings",
                {
                    "user_id": user_id,
                    "secret": secret,
                    "backup_codes": backup_codes,
                    "enabled": False,
                    "setup_at": "now()",
                },
                on_conflict="user_id",
            )

            logger.info(f"MFA setup initiated for user {user_id}")

            return MFASetupResponse(
                secret=secret,
                qr_code_url=qr_code_url,
                backup_codes=backup_codes,
                manual_entry_key=secret,
            )

        except Exception as e:
            logger.error(f"Failed to setup MFA for user {user_id}: {e}")
            raise CoreServiceError(
                message="Failed to setup MFA",
                code="MFA_SETUP_FAILED",
                service="MFAService",
                details={"user_id": user_id, "error": str(e)},
            ) from e

    async def enroll_mfa(self, request: MFAEnrollmentRequest) -> MFAEnrollmentResponse:
        """
        Complete MFA enrollment by verifying the TOTP code.

        Args:
            request: MFA enrollment request with verification code

        Returns:
            MFA enrollment response

        Raises:
            CoreValidationError: If TOTP code is invalid
            CoreServiceError: If enrollment fails
        """
        try:
            await self._ensure_db()

            # Get user's MFA setup
            mfa_data = await self.db.select(
                "user_mfa_settings", "*", {"user_id": request.user_id}
            )

            if not mfa_data:
                raise CoreValidationError(
                    message="MFA not set up for this user",
                    code="MFA_NOT_SETUP",
                    field="user_id",
                )

            mfa_settings = mfa_data[0]
            if mfa_settings.get("enabled"):
                raise CoreValidationError(
                    message="MFA already enrolled",
                    code="MFA_ALREADY_ENROLLED",
                    field="user_id",
                )

            # Verify TOTP code
            totp = pyotp.TOTP(mfa_settings["secret"])
            if not totp.verify(request.totp_code, valid_window=1):
                raise CoreValidationError(
                    message="Invalid TOTP code",
                    code="INVALID_TOTP_CODE",
                    field="totp_code",
                )

            # Enable MFA
            await self.db.update(
                "user_mfa_settings",
                {"user_id": request.user_id},
                {"enabled": True, "enrolled_at": "now()", "last_used": "now()"},
            )

            logger.info(f"MFA enrolled successfully for user {request.user_id}")

            return MFAEnrollmentResponse(
                backup_codes=mfa_settings["backup_codes"],
                enrolled_at="now()",
                success=True,
            )

        except (CoreValidationError, CoreServiceError):
            raise
        except Exception as e:
            logger.error(f"Failed to enroll MFA for user {request.user_id}: {e}")
            raise CoreServiceError(
                message="Failed to enroll MFA",
                code="MFA_ENROLLMENT_FAILED",
                service="MFAService",
                details={"user_id": request.user_id, "error": str(e)},
            ) from e

    async def verify_mfa(
        self, request: MFAVerificationRequest
    ) -> MFAVerificationResponse:
        """
        Verify MFA code (TOTP or backup code).

        Args:
            request: MFA verification request

        Returns:
            MFA verification response

        Raises:
            CoreServiceError: If verification fails
        """
        try:
            await self._ensure_db()

            # Get user's MFA settings
            mfa_data = await self.db.select(
                "user_mfa_settings", "*", {"user_id": request.user_id, "enabled": True}
            )

            if not mfa_data:
                return MFAVerificationResponse(valid=False, code_type="none")

            mfa_settings = mfa_data[0]

            # Try TOTP verification first
            totp = pyotp.TOTP(mfa_settings["secret"])
            if totp.verify(request.code, valid_window=1):
                # Update last used
                await self.db.update(
                    "user_mfa_settings",
                    {"user_id": request.user_id},
                    {"last_used": "now()"},
                )

                return MFAVerificationResponse(valid=True, code_type="totp")

            # Try backup code verification
            backup_codes = mfa_settings.get("backup_codes", [])
            if request.code in backup_codes:
                # Remove used backup code
                backup_codes.remove(request.code)

                await self.db.update(
                    "user_mfa_settings",
                    {"user_id": request.user_id},
                    {"backup_codes": backup_codes, "last_used": "now()"},
                )

                logger.info(f"Backup code used for user {request.user_id}")

                return MFAVerificationResponse(
                    valid=True,
                    code_type="backup",
                    remaining_backup_codes=len(backup_codes),
                )

            # Invalid code
            return MFAVerificationResponse(valid=False, code_type="invalid")

        except Exception as e:
            logger.error(f"Failed to verify MFA for user {request.user_id}: {e}")
            raise CoreServiceError(
                message="Failed to verify MFA",
                code="MFA_VERIFICATION_FAILED",
                service="MFAService",
                details={"user_id": request.user_id, "error": str(e)},
            ) from e

    async def get_mfa_status(self, user_id: str) -> MFAStatus:
        """
        Get MFA status for a user.

        Args:
            user_id: User ID

        Returns:
            MFA status
        """
        try:
            await self._ensure_db()

            mfa_data = await self.db.select(
                "user_mfa_settings", "*", {"user_id": user_id}
            )

            if not mfa_data:
                return MFAStatus(enabled=False)

            mfa_settings = mfa_data[0]

            return MFAStatus(
                enabled=mfa_settings.get("enabled", False),
                enrolled_at=mfa_settings.get("enrolled_at"),
                backup_codes_remaining=len(mfa_settings.get("backup_codes", [])),
                last_used=mfa_settings.get("last_used"),
            )

        except Exception as e:
            logger.error(f"Failed to get MFA status for user {user_id}: {e}")
            return MFAStatus(enabled=False)

    async def disable_mfa(self, user_id: str) -> bool:
        """
        Disable MFA for a user.

        Args:
            user_id: User ID

        Returns:
            True if disabled successfully
        """
        try:
            await self._ensure_db()

            result = await self.db.delete("user_mfa_settings", {"user_id": user_id})

            logger.info(f"MFA disabled for user {user_id}")
            return len(result) > 0

        except Exception as e:
            logger.error(f"Failed to disable MFA for user {user_id}: {e}")
            return False

    async def regenerate_backup_codes(self, user_id: str) -> List[str]:
        """
        Regenerate backup codes for a user.

        Args:
            user_id: User ID

        Returns:
            New backup codes

        Raises:
            CoreServiceError: If regeneration fails
        """
        try:
            await self._ensure_db()

            # Check if MFA is enabled
            mfa_data = await self.db.select(
                "user_mfa_settings", "*", {"user_id": user_id, "enabled": True}
            )

            if not mfa_data:
                raise CoreServiceError(
                    message="MFA not enabled for this user",
                    code="MFA_NOT_ENABLED",
                    service="MFAService",
                )

            # Generate new backup codes
            backup_codes = self._generate_backup_codes()

            # Update in database
            await self.db.update(
                "user_mfa_settings",
                {"user_id": user_id},
                {"backup_codes": backup_codes},
            )

            logger.info(f"Backup codes regenerated for user {user_id}")
            return backup_codes

        except CoreServiceError:
            raise
        except Exception as e:
            logger.error(f"Failed to regenerate backup codes for user {user_id}: {e}")
            raise CoreServiceError(
                message="Failed to regenerate backup codes",
                code="BACKUP_CODES_REGENERATION_FAILED",
                service="MFAService",
                details={"user_id": user_id, "error": str(e)},
            ) from e

    def _generate_qr_code(self, provisioning_uri: str) -> str:
        """
        Generate QR code as data URL.

        Args:
            provisioning_uri: TOTP provisioning URI

        Returns:
            Data URL for QR code image
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to data URL
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{img_str}"

    def _generate_backup_codes(self, count: int = 10) -> List[str]:
        """
        Generate backup codes.

        Args:
            count: Number of backup codes to generate

        Returns:
            List of backup codes
        """
        return [
            f"{secrets.randbelow(100000):05d}-{secrets.randbelow(100000):05d}"
            for _ in range(count)
        ]


# Dependency function for FastAPI
async def get_mfa_service() -> MFAService:
    """Get MFA service instance for dependency injection."""
    return MFAService()
