"""API key management service for TripSage API.

This module provides services for API key management, including BYOK (Bring Your Own Key)
functionality for user-provided API keys.
"""

import base64
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from tripsage.api.core.config import get_settings
from tripsage.api.models.api_key import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyValidateResponse,
)
from tripsage.api.services.key_monitoring import (
    KeyMonitoringService,
    KeyOperation,
    constant_time_compare,
    monitor_key_operation,
    secure_random_token,
)
from tripsage.mcp_abstraction import mcp_manager

logger = logging.getLogger(__name__)


class KeyService:
    """API key management service for the TripSage API.

    This service handles API key management, including key creation,
    retrieval, validation, and rotation.
    """

    def __init__(self):
        """Initialize the key service."""
        self.mcp_manager = mcp_manager
        self.settings = get_settings()
        self.supabase_mcp = None
        self.monitoring_service = None
        self.initialized = False

        # Initialize the key encryption system
        self._initialize_encryption()
        
    async def initialize(self):
        """Initialize connections and services."""
        if not self.initialized:
            # Initialize Supabase MCP
            self.supabase_mcp = await self.mcp_manager.initialize_mcp("supabase")
            
            # Initialize monitoring service
            self.monitoring_service = KeyMonitoringService()
            await self.monitoring_service.initialize()
            
            self.initialized = True

    def _initialize_encryption(self):
        """Initialize the encryption system for API keys.

        We use a two-layer encryption system (envelope encryption):
        1. A master key derived from a secret stored in the environment
        2. A data key for each API key encrypted with the master key
        """
        # Get the master key from environment
        master_key_secret = os.environ.get(
            "API_KEY_MASTER_SECRET",
            self.settings.secret_key,  # Fallback to app secret
        )

        # Create a key derivation function
        salt = b"tripsage_api_key_salt"  # Static salt is fine for this purpose
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 32 bytes = 256 bits
            salt=salt,
            iterations=100000,  # NIST recommended minimum
        )

        # Derive the master key
        key_bytes = kdf.derive(master_key_secret.encode())
        self.master_key = base64.urlsafe_b64encode(key_bytes)

        # Create the Fernet cipher
        self.cipher = Fernet(self.master_key)

    def _encrypt_api_key(self, key: str) -> str:
        """Encrypt an API key.

        Args:
            key: The API key to encrypt

        Returns:
            The encrypted API key
        """
        # Generate a data key for this API key
        data_key = Fernet.generate_key()
        data_cipher = Fernet(data_key)

        # Encrypt the API key with the data key
        encrypted_key = data_cipher.encrypt(key.encode())

        # Encrypt the data key with the master key
        encrypted_data_key = self.cipher.encrypt(data_key)

        # Combine the encrypted data key and encrypted API key
        combined = base64.urlsafe_b64encode(encrypted_data_key + b"." + encrypted_key)

        return combined.decode()

    def _decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt an API key.

        Args:
            encrypted_key: The encrypted API key

        Returns:
            The decrypted API key

        Raises:
            Exception: If decryption fails
        """
        try:
            # Decode the combined encrypted data
            combined = base64.urlsafe_b64decode(encrypted_key.encode())

            # Split the encrypted data key and encrypted API key
            parts = combined.split(b".", 1)
            if len(parts) != 2:
                raise ValueError("Invalid encrypted key format")

            encrypted_data_key, encrypted_key = parts

            # Decrypt the data key with the master key
            data_key = self.cipher.decrypt(encrypted_data_key)

            # Decrypt the API key with the data key
            data_cipher = Fernet(data_key)
            decrypted_key = data_cipher.decrypt(encrypted_key)

            return decrypted_key.decode()
        except Exception as e:
            logger.error(f"Error decrypting API key: {e}")
            raise

    async def list_keys(self, user_id: str) -> List[ApiKeyResponse]:
        """List all API keys for a user.

        Args:
            user_id: The user ID

        Returns:
            List of API keys
        """
        try:
            # Use Supabase MCP to get the keys
            supabase_mcp = await self.mcp_manager.initialize_mcp("supabase")

            result = await supabase_mcp.invoke_method(
                "query",
                params={
                    "table": "api_keys",
                    "query": {"user_id": user_id, "select": "*"},
                },
            )

            if not result or not result.get("data"):
                return []

            # Convert to API key response models
            keys = []
            now = datetime.utcnow()

            for key_data in result["data"]:
                # Check if the key is expired
                is_valid = True
                if (
                    key_data.get("expires_at")
                    and datetime.fromisoformat(
                        key_data["expires_at"].replace("Z", "+00:00")
                    )
                    < now
                ):
                    is_valid = False

                keys.append(
                    ApiKeyResponse(
                        id=key_data["id"],
                        name=key_data["name"],
                        service=key_data["service"],
                        description=key_data.get("description"),
                        created_at=key_data["created_at"],
                        updated_at=key_data["updated_at"],
                        expires_at=key_data.get("expires_at"),
                        is_valid=is_valid,
                        last_used=key_data.get("last_used"),
                    )
                )

            return keys
        except Exception as e:
            logger.error(f"Error listing API keys: {e}")
            return []

    async def get_key(self, key_id: str) -> Optional[dict]:
        """Get an API key by ID.

        Args:
            key_id: The API key ID

        Returns:
            The API key if found, None otherwise
        """
        try:
            # Use Supabase MCP to get the key
            supabase_mcp = await self.mcp_manager.initialize_mcp("supabase")

            result = await supabase_mcp.invoke_method(
                "query",
                params={
                    "table": "api_keys",
                    "query": {"id": key_id, "select": "*"},
                },
            )

            if not result or not result.get("data") or len(result["data"]) == 0:
                return None

            return result["data"][0]
        except Exception as e:
            logger.error(f"Error getting API key: {e}")
            return None

    async def create_key(self, user_id: str, key_data: ApiKeyCreate) -> ApiKeyResponse:
        """Create a new API key.

        Args:
            user_id: The user ID
            key_data: API key data

        Returns:
            The created API key

        Raises:
            Exception: If the key cannot be created
        """
        try:
            # Generate a key ID
            key_id = str(uuid.uuid4())

            # Encrypt the API key
            encrypted_key = self._encrypt_api_key(key_data.key)

            # Current time
            now = datetime.utcnow()

            # Use Supabase MCP to create the key
            supabase_mcp = await self.mcp_manager.initialize_mcp("supabase")

            result = await supabase_mcp.invoke_method(
                "insert",
                params={
                    "table": "api_keys",
                    "data": {
                        "id": key_id,
                        "user_id": user_id,
                        "name": key_data.name,
                        "service": key_data.service,
                        "encrypted_key": encrypted_key,
                        "description": key_data.description,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                        "expires_at": key_data.expires_at.isoformat()
                        if key_data.expires_at
                        else None,
                    },
                },
            )

            if not result or not result.get("data") or len(result["data"]) == 0:
                raise Exception("Failed to create API key")

            key_data = result["data"][0]

            # Create API key response model
            return ApiKeyResponse(
                id=key_data["id"],
                name=key_data["name"],
                service=key_data["service"],
                description=key_data.get("description"),
                created_at=key_data["created_at"],
                updated_at=key_data["updated_at"],
                expires_at=key_data.get("expires_at"),
                is_valid=True,
                last_used=None,
            )
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            raise

    async def delete_key(self, key_id: str) -> bool:
        """Delete an API key.

        Args:
            key_id: The API key ID

        Returns:
            True if the key was deleted, False otherwise
        """
        try:
            # Use Supabase MCP to delete the key
            supabase_mcp = await self.mcp_manager.initialize_mcp("supabase")

            result = await supabase_mcp.invoke_method(
                "delete",
                params={
                    "table": "api_keys",
                    "query": {"id": key_id},
                },
            )

            return result and result.get("count", 0) > 0
        except Exception as e:
            logger.error(f"Error deleting API key: {e}")
            return False

    async def rotate_key(self, key_id: str, new_key: str) -> ApiKeyResponse:
        """Rotate an API key.

        Args:
            key_id: The API key ID
            new_key: The new API key

        Returns:
            The updated API key

        Raises:
            Exception: If the key cannot be rotated
        """
        try:
            # Get the key
            key = await self.get_key(key_id)
            if not key:
                raise Exception("API key not found")

            # Encrypt the new API key
            encrypted_key = self._encrypt_api_key(new_key)

            # Current time
            now = datetime.utcnow()

            # Use Supabase MCP to update the key
            supabase_mcp = await self.mcp_manager.initialize_mcp("supabase")

            result = await supabase_mcp.invoke_method(
                "update",
                params={
                    "table": "api_keys",
                    "query": {"id": key_id},
                    "data": {
                        "encrypted_key": encrypted_key,
                        "updated_at": now.isoformat(),
                    },
                },
            )

            if not result or not result.get("data") or len(result["data"]) == 0:
                raise Exception("Failed to rotate API key")

            key_data = result["data"][0]

            # Create API key response model
            return ApiKeyResponse(
                id=key_data["id"],
                name=key_data["name"],
                service=key_data["service"],
                description=key_data.get("description"),
                created_at=key_data["created_at"],
                updated_at=key_data["updated_at"],
                expires_at=key_data.get("expires_at"),
                is_valid=True,
                last_used=key_data.get("last_used"),
            )
        except Exception as e:
            logger.error(f"Error rotating API key: {e}")
            raise

    @monitor_key_operation(KeyOperation.VALIDATE)
    async def validate_key(
        self,
        key: str,
        service: str,
        user_id: Optional[str] = None,
        monitoring_service: Optional[KeyMonitoringService] = None,
    ) -> ApiKeyValidateResponse:
        """Validate an API key with the service.

        Args:
            key: The API key to validate
            service: The service to validate against
            user_id: Optional user ID for monitoring
            monitoring_service: Optional monitoring service

        Returns:
            Validation result
        """
        try:
            # Initialize the MCP for the service
            mcp = await self.mcp_manager.initialize_mcp(service)

            # Validate the key using the MCP
            result = await mcp.invoke_method(
                "validate_key",
                params={"key": key},
            )

            # Check if the key is valid
            if result and result.get("valid"):
                return ApiKeyValidateResponse(
                    is_valid=True,
                    service=service,
                    message="API key is valid",
                )
            else:
                # Use constant time comparison even on invalid keys to prevent timing attacks
                constant_time_compare(key, secure_random_token(len(key)))

                return ApiKeyValidateResponse(
                    is_valid=False,
                    service=service,
                    message=result.get("message", "API key is invalid"),
                )
        except Exception as e:
            logger.error(f"Error validating API key: {e}")

            # Use constant time comparison to avoid timing attacks even on errors
            constant_time_compare(key, secure_random_token(len(key)))

            return ApiKeyValidateResponse(
                is_valid=False,
                service=service,
                message=f"Error validating API key: {str(e)}",
            )

    async def get_key_for_service(self, user_id: str, service: str) -> Optional[str]:
        """Get a decrypted API key for a service.

        Args:
            user_id: The user ID
            service: The service name

        Returns:
            The decrypted API key if found, None otherwise
        """
        try:
            # Use Supabase MCP to get the key
            supabase_mcp = await self.mcp_manager.initialize_mcp("supabase")

            result = await supabase_mcp.invoke_method(
                "query",
                params={
                    "table": "api_keys",
                    "query": {
                        "user_id": user_id,
                        "service": service,
                        "select": "*",
                    },
                    "order": {"column": "updated_at", "direction": "desc"},
                    "limit": 1,
                },
            )

            if not result or not result.get("data") or len(result["data"]) == 0:
                return None

            key_data = result["data"][0]

            # Check if the key is expired
            now = datetime.utcnow()
            if (
                key_data.get("expires_at")
                and datetime.fromisoformat(
                    key_data["expires_at"].replace("Z", "+00:00")
                )
                < now
            ):
                logger.warning(f"API key for {service} has expired")
                return None

            # Decrypt the API key
            encrypted_key = key_data["encrypted_key"]
            decrypted_key = self._decrypt_api_key(encrypted_key)

            # Update last used timestamp
            await supabase_mcp.invoke_method(
                "update",
                params={
                    "table": "api_keys",
                    "query": {"id": key_data["id"]},
                    "data": {"last_used": now.isoformat()},
                },
            )

            return decrypted_key
        except Exception as e:
            logger.error(f"Error getting API key for service: {e}")
            return None
