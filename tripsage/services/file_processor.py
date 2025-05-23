"""
File processing service for handling uploads, storage, and metadata management.

This service implements the core business logic for file handling following
KISS principles with local storage initially.
"""

import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import UploadFile, HTTPException
from pydantic import BaseModel, Field

from tripsage.utils.file_validation import ValidationResult, validate_file
from tripsage.models.db.user import UserDB


class ProcessedFile(BaseModel):
    """Processed file metadata."""
    
    file_id: str = Field(..., description="Unique file identifier")
    user_id: str = Field(..., description="Owner user ID")
    original_filename: str = Field(..., description="Original uploaded filename")
    stored_filename: str = Field(..., description="Filename used for storage")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="Detected MIME type")
    file_hash: str = Field(..., description="SHA256 hash for deduplication")
    storage_path: str = Field(..., description="Relative storage path")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")
    processing_status: str = Field(default="pending", description="Processing status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional file metadata")
    analysis_results: Optional[Dict[str, Any]] = Field(None, description="AI analysis results")


class FileProcessor:
    """
    Service for processing uploaded files with storage and metadata management.
    
    Follows KISS principle - starts with local file storage, can be extended
    to cloud storage when needed.
    """
    
    def __init__(self, storage_root: str = "uploads"):
        """
        Initialize file processor.
        
        Args:
            storage_root: Root directory for file storage
        """
        self.storage_root = Path(storage_root)
        self.storage_root.mkdir(exist_ok=True)
        
        # Create user-specific subdirectories as needed
        self._ensure_storage_structure()
    
    def _ensure_storage_structure(self) -> None:
        """Ensure proper storage directory structure exists."""
        # Create basic structure
        (self.storage_root / "files").mkdir(exist_ok=True)
        (self.storage_root / "temp").mkdir(exist_ok=True)
        (self.storage_root / "processed").mkdir(exist_ok=True)
    
    async def process_file(self, file: UploadFile, user_id: str) -> ProcessedFile:
        """
        Process a single uploaded file.
        
        Args:
            file: FastAPI UploadFile object
            user_id: ID of the uploading user
            
        Returns:
            ProcessedFile with metadata and storage information
            
        Raises:
            HTTPException: If processing fails
        """
        try:
            # Validate file first
            validation_result = await validate_file(file)
            if not validation_result.is_valid:
                raise HTTPException(status_code=400, detail=validation_result.error_message)
            
            # Generate unique file ID and storage path
            file_id = str(uuid4())
            user_storage_dir = self._get_user_storage_dir(user_id)
            user_storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate safe filename
            safe_filename = self._generate_safe_filename(file.filename, file_id)
            storage_path = user_storage_dir / safe_filename
            
            # Save file to storage
            await self._save_file_to_storage(file, storage_path)
            
            # Create processed file metadata
            processed_file = ProcessedFile(
                file_id=file_id,
                user_id=user_id,
                original_filename=file.filename,
                stored_filename=safe_filename,
                file_size=validation_result.file_size,
                mime_type=validation_result.detected_type,
                file_hash=validation_result.file_hash,
                storage_path=str(storage_path.relative_to(self.storage_root)),
                processing_status="stored"
            )
            
            # Extract basic metadata
            metadata = await self._extract_file_metadata(storage_path, validation_result.detected_type)
            processed_file.metadata = metadata
            
            # TODO: Store metadata in database when ready
            # await self._store_file_metadata(processed_file)
            
            return processed_file
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")
    
    async def process_batch(self, files: List[UploadFile], user_id: str) -> List[ProcessedFile]:
        """
        Process multiple files in batch.
        
        Args:
            files: List of UploadFile objects
            user_id: ID of the uploading user
            
        Returns:
            List of ProcessedFile objects
        """
        processed_files = []
        errors = []
        
        # Process files concurrently for better performance
        tasks = [self.process_file(file, user_id) for file in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"File {files[i].filename}: {str(result)}")
            else:
                processed_files.append(result)
        
        if errors and not processed_files:
            # All files failed
            raise HTTPException(status_code=400, detail=f"All files failed to process: {'; '.join(errors)}")
        elif errors:
            # Some files failed - log errors but return successful ones
            # TODO: Add proper logging when logging service is ready
            pass
        
        return processed_files
    
    async def get_file_metadata(self, file_id: str, user_id: str) -> Optional[ProcessedFile]:
        """
        Retrieve file metadata by ID.
        
        Args:
            file_id: Unique file identifier
            user_id: User ID for security validation
            
        Returns:
            ProcessedFile metadata or None if not found
        """
        # TODO: Query database when ready
        # For now, return None as this is a placeholder
        return None
    
    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """
        Delete a file and its metadata.
        
        Args:
            file_id: Unique file identifier
            user_id: User ID for security validation
            
        Returns:
            True if deleted successfully
        """
        try:
            # TODO: Query database to get file path when ready
            # For now, this is a placeholder implementation
            
            # In actual implementation:
            # 1. Query database for file metadata
            # 2. Verify user ownership
            # 3. Delete physical file
            # 4. Delete database record
            
            return True
            
        except Exception:
            return False
    
    async def list_user_files(self, user_id: str, limit: int = 50, offset: int = 0) -> List[ProcessedFile]:
        """
        List files for a specific user.
        
        Args:
            user_id: User ID to list files for
            limit: Maximum number of files to return
            offset: Number of files to skip
            
        Returns:
            List of ProcessedFile objects
        """
        # TODO: Query database when ready
        # For now, return empty list as placeholder
        return []
    
    def _get_user_storage_dir(self, user_id: str) -> Path:
        """Get storage directory for a specific user."""
        return self.storage_root / "files" / user_id
    
    def _generate_safe_filename(self, original_filename: str, file_id: str) -> str:
        """
        Generate a safe filename for storage.
        
        Args:
            original_filename: Original uploaded filename
            file_id: Unique file ID
            
        Returns:
            Safe filename string
        """
        # Extract extension
        file_path = Path(original_filename)
        extension = file_path.suffix.lower()
        
        # Use file_id as base name for uniqueness
        return f"{file_id}{extension}"
    
    async def _save_file_to_storage(self, file: UploadFile, storage_path: Path) -> None:
        """
        Save uploaded file to storage location.
        
        Args:
            file: UploadFile object
            storage_path: Path where file should be stored
        """
        try:
            # Read file content
            content = await file.read()
            
            # Write to storage
            with open(storage_path, "wb") as f:
                f.write(content)
                
            # Reset file pointer for potential future reads
            await file.seek(0)
            
        except Exception as e:
            # Clean up partial file if exists
            if storage_path.exists():
                storage_path.unlink()
            raise e
    
    async def _extract_file_metadata(self, file_path: Path, mime_type: str) -> Dict[str, Any]:
        """
        Extract metadata from stored file.
        
        Args:
            file_path: Path to stored file
            mime_type: Detected MIME type
            
        Returns:
            Dictionary of extracted metadata
        """
        metadata = {
            "file_extension": file_path.suffix,
            "storage_timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Add type-specific metadata
            if mime_type.startswith("image/"):
                # TODO: Add image metadata extraction (dimensions, etc.)
                pass
            elif mime_type == "application/pdf":
                # TODO: Add PDF metadata extraction (pages, etc.)
                pass
            elif mime_type in ["text/plain", "text/csv"]:
                # Add text file metadata
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    metadata["line_count"] = len(content.splitlines())
                    metadata["character_count"] = len(content)
        
        except Exception:
            # If metadata extraction fails, continue with basic metadata
            pass
        
        return metadata
    
    async def get_file_content(self, file_id: str, user_id: str) -> Optional[bytes]:
        """
        Retrieve raw file content by ID.
        
        Args:
            file_id: Unique file identifier
            user_id: User ID for security validation
            
        Returns:
            File content bytes or None if not found
        """
        try:
            # TODO: Query database to get file path when ready
            # For now, this is a placeholder
            return None
            
        except Exception:
            return None
    
    async def get_storage_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get storage statistics for a user.
        
        Args:
            user_id: User ID to get stats for
            
        Returns:
            Dictionary with storage statistics
        """
        user_dir = self._get_user_storage_dir(user_id)
        
        if not user_dir.exists():
            return {
                "total_files": 0,
                "total_size": 0,
                "storage_used": "0 MB"
            }
        
        total_files = 0
        total_size = 0
        
        for file_path in user_dir.rglob("*"):
            if file_path.is_file():
                total_files += 1
                total_size += file_path.stat().st_size
        
        return {
            "total_files": total_files,
            "total_size": total_size,
            "storage_used": f"{total_size / (1024 * 1024):.2f} MB"
        }


# Dependency injection function for FastAPI
def get_file_processor() -> FileProcessor:
    """
    Get FileProcessor instance for dependency injection.
    
    Returns:
        FileProcessor instance
    """
    # TODO: Configure storage path from settings when ready
    return FileProcessor()