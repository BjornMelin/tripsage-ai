"""File attachment router for TripSage API.

This module provides endpoints for secure file uploads, processing, and AI analysis
of travel documents, following KISS principles and security best practices.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from tripsage.api.core.dependencies import get_current_user
from tripsage.services.file_processor import FileProcessor
from tripsage_core.models.db.user import UserDB
from tripsage_core.utils.file_utils import MAX_SESSION_SIZE, validate_file

logger = logging.getLogger(__name__)

router = APIRouter()

# File configuration now imported from centralized config

# Module-level dependencies to avoid B008 warnings
get_current_user_dep = Depends(get_current_user)

# Module-level dependency for file uploads
file_upload_dep = File(...)
files_upload_dep = File(...)


def get_file_processor() -> FileProcessor:
    """Get file processor singleton."""
    # Choice: Using simple import pattern instead of complex DI
    # Reason: KISS principle - FileProcessor is lightweight and stateless
    return FileProcessor()


get_file_processor_dep = Depends(get_file_processor)


class FileUploadResponse(BaseModel):
    """Response model for file upload."""

    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    processing_status: str = Field(..., description="Processing status")
    upload_status: str = Field(..., description="Upload status")
    message: str = Field(default="Upload successful", description="Status message")


class BatchUploadResponse(BaseModel):
    """Response model for batch file upload."""

    files: List[FileUploadResponse] = Field(..., description="Processed files")
    total_files: int = Field(..., description="Total files processed")
    total_size: int = Field(..., description="Total size in bytes")


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = file_upload_dep,
    current_user: UserDB = get_current_user_dep,
    processor: FileProcessor = get_file_processor_dep,
):
    """Upload and process a single file attachment.

    Security features:
    - File type validation
    - Size limit enforcement
    - Virus scanning (when available)
    - User isolation

    AI features:
    - Document text extraction
    - Travel information analysis
    - Structured data extraction
    """
    # Validate file
    validation_result = await validate_file(file)
    if not validation_result.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_result.error_message,
        )

    try:
        # Process file with user context
        result = await processor.process_file(file, current_user.id)

        logger.info(
            f"File uploaded successfully: {file.filename} "
            f"({result.file_size} bytes) for user {current_user.id}"
        )

        return FileUploadResponse(
            file_id=result.file_id,
            filename=result.original_filename,
            file_size=result.file_size,
            mime_type=result.mime_type,
            processing_status=result.processing_status,
            upload_status="completed",
            message="Upload successful",
        )

    except Exception as e:
        logger.error(f"File processing failed for {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File processing failed",
        ) from e


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_files_batch(
    files: List[UploadFile] = files_upload_dep,
    current_user: UserDB = get_current_user_dep,
    processor: FileProcessor = get_file_processor_dep,
):
    """Upload and process multiple files in a batch.

    Validates total session size limit and processes files individually
    for better error handling and progress tracking.
    """
    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided"
        )

    # Calculate total size for session limit validation
    # Note: UploadFile doesn't expose size directly, we'll validate during processing
    total_size = 0
    for file in files:
        # Read to get content length, then reset
        content = await file.read()
        total_size += len(content)
        await file.seek(0)
    if total_size > MAX_SESSION_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Total file size ({total_size} bytes) exceeds session limit "
            f"({MAX_SESSION_SIZE} bytes)",
        )

    processed_files = []
    errors = []

    # Process each file individually for better error isolation
    for file in files:
        try:
            # Validate file
            validation_result = await validate_file(file)
            if not validation_result.is_valid:
                errors.append(f"{file.filename}: {validation_result.error_message}")
                continue

            # Process file
            result = await processor.process_file(file, current_user.id)
            processed_files.append(
                FileUploadResponse(
                    file_id=result.file_id,
                    filename=result.original_filename,
                    file_size=result.file_size,
                    mime_type=result.mime_type,
                    processing_status=result.processing_status,
                    upload_status="completed",
                    message="Upload successful",
                )
            )

        except Exception as e:
            logger.error(f"Failed to process file {file.filename}: {str(e)}")
            errors.append(f"{file.filename}: Processing failed")

    if errors and not processed_files:
        # All files failed
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"All files failed validation/processing: {'; '.join(errors)}",
        )

    if errors:
        # Some files failed - log warnings but return successful ones
        logger.warning(f"Some files failed processing: {'; '.join(errors)}")

    logger.info(
        f"Batch upload completed: {len(processed_files)}/{len(files)} files "
        f"processed for user {current_user.id}"
    )

    return BatchUploadResponse(
        files=processed_files,
        total_files=len(processed_files),
        total_size=sum(f.file_size for f in processed_files),
    )


@router.get("/files/{file_id}")
async def get_file_metadata(
    file_id: str,
    current_user: UserDB = get_current_user_dep,
    processor: FileProcessor = get_file_processor_dep,
):
    """Get metadata and analysis results for an uploaded file.

    Only returns files owned by the current user for security.
    """
    try:
        file_info = await processor.get_file_metadata(file_id, current_user.id)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied",
            )

        return file_info

    except Exception as e:
        logger.error(f"Failed to get file info for {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file information",
        ) from e


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: UserDB = get_current_user_dep,
    processor: FileProcessor = get_file_processor_dep,
):
    """Delete an uploaded file and its associated data.

    Only allows deletion of files owned by the current user.
    """
    try:
        success = await processor.delete_file(file_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied",
            )

        logger.info(f"File {file_id} deleted by user {current_user.id}")
        return {"message": "File deleted successfully", "file_id": file_id}

    except Exception as e:
        logger.error(f"Failed to delete file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file",
        ) from e


@router.get("/files")
async def list_user_files(
    current_user: UserDB = get_current_user_dep,
    processor: FileProcessor = get_file_processor_dep,
    limit: int = 50,
    offset: int = 0,
):
    """List files uploaded by the current user with pagination."""
    try:
        files = await processor.list_user_files(
            current_user.id, limit=limit, offset=offset
        )

        return {
            "files": files,
            "limit": limit,
            "offset": offset,
            "total": len(files),  # Simple implementation - could be optimized
        }

    except Exception as e:
        logger.error(f"Failed to list files for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file list",
        ) from e
