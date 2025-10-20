"""File attachment router for TripSage API.

This module provides endpoints for secure file uploads, processing, and AI analysis
of travel documents, following KISS principles and security best practices.
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from tripsage.api.core.dependencies import get_principal_id, require_principal
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditSeverity,
    audit_security_event,
)
from tripsage_core.services.business.file_processing_service import (
    FileProcessingService,
    FileSearchRequest,
    FileUploadRequest,
)
from tripsage_core.services.business.trip_service import TripService, get_trip_service
from tripsage_core.utils.file_utils import MAX_SESSION_SIZE, validate_file


logger = logging.getLogger(__name__)

router = APIRouter()

# File configuration now imported from centralized config

# Module-level dependencies to avoid B008 warnings
require_principal_module_dep = Depends(require_principal)

# Module-level dependency for file uploads
file_upload_dep = File(...)
files_upload_dep = File(...)


def get_file_processing_service() -> FileProcessingService:
    """Get file processing service singleton."""
    # Choice: Using simple import pattern instead of complex DI
    # Reason: KISS principle - FileProcessingService is lightweight and stateless
    return FileProcessingService()


get_file_processing_service_dep = Depends(get_file_processing_service)
get_trip_service_dep = Depends(get_trip_service)


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

    files: list[FileUploadResponse] = Field(..., description="Processed files")
    total_files: int = Field(..., description="Total files processed")
    total_size: int = Field(..., description="Total size in bytes")


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = file_upload_dep,
    principal: Principal = require_principal_module_dep,
    service: FileProcessingService = get_file_processing_service_dep,
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
        user_id = get_principal_id(principal)

        # Read file content
        content = await file.read()

        # Create upload request
        upload_request = FileUploadRequest(
            filename=file.filename, content=content, auto_analyze=True
        )

        # Process file
        result = await service.upload_file(user_id, upload_request)

        logger.info(
            f"File uploaded successfully: {file.filename} ({result.file_size} bytes) "
            f"for user {user_id}"
        )

        return FileUploadResponse(
            file_id=result.id,
            filename=result.original_filename,
            file_size=result.file_size,
            mime_type=result.mime_type,
            processing_status=result.processing_status.value,
            upload_status="completed",
            message="Upload successful",
        )

    except Exception as e:
        logger.exception(f"File processing failed for {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File processing failed",
        ) from e


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_files_batch(
    files: list[UploadFile] = files_upload_dep,
    principal: Principal = require_principal_module_dep,
    service: FileProcessingService = get_file_processing_service_dep,
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
            detail=(
                f"Total file size ({total_size} bytes) exceeds session limit "
                f"({MAX_SESSION_SIZE} bytes)"
            ),
        )

    processed_files = []
    errors = []
    user_id = get_principal_id(principal)

    # Process each file individually for better error isolation
    for file in files:
        try:
            # Validate file
            validation_result = await validate_file(file)
            if not validation_result.is_valid:
                errors.append(f"{file.filename}: {validation_result.error_message}")
                continue

            # Read file content
            content = await file.read()

            # Create upload request
            upload_request = FileUploadRequest(
                filename=file.filename, content=content, auto_analyze=True
            )

            # Process file
            result = await service.upload_file(user_id, upload_request)
            processed_files.append(
                FileUploadResponse(
                    file_id=result.id,
                    filename=result.original_filename,
                    file_size=result.file_size,
                    mime_type=result.mime_type,
                    processing_status=result.processing_status.value,
                    upload_status="completed",
                    message="Upload successful",
                )
            )

        except Exception:
            logger.exception(f"Failed to process file {file.filename}")
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
        f"Batch upload completed: {len(processed_files)}/{len(files)} files processed "
        f"for user {user_id}"
    )

    return BatchUploadResponse(
        files=processed_files,
        total_files=len(processed_files),
        total_size=sum(f.file_size for f in processed_files),
    )


@router.get("/files/{file_id}")
async def get_file_metadata(
    file_id: str,
    principal: Principal = require_principal_module_dep,
    service: FileProcessingService = get_file_processing_service_dep,
):
    """Get metadata and analysis results for an uploaded file.

    Only returns files owned by the current user for security.
    """
    try:
        user_id = get_principal_id(principal)
        file_info = await service.get_file(file_id, user_id)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied",
            )

        return file_info

    except Exception as e:
        logger.exception(f"Failed to get file info for {file_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file information",
        ) from e


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    principal: Principal = require_principal_module_dep,
    service: FileProcessingService = get_file_processing_service_dep,
):
    """Delete an uploaded file and its associated data.

    Only allows deletion of files owned by the current user.
    """
    try:
        user_id = get_principal_id(principal)
        success = await service.delete_file(file_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied",
            )

        logger.info(f"File {file_id} deleted by user {user_id}")
        return {"message": "File deleted successfully", "file_id": file_id}

    except Exception as e:
        logger.exception(f"Failed to delete file {file_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file",
        ) from e


@router.get("/files")
async def list_user_files(
    principal: Principal = require_principal_module_dep,
    service: FileProcessingService = get_file_processing_service_dep,
    limit: int = 50,
    offset: int = 0,
):
    """List files uploaded by the current user with pagination."""
    try:
        user_id = get_principal_id(principal)

        # Create search request with basic pagination
        search_request = FileSearchRequest(limit=limit, offset=offset)

        files = await service.search_files(user_id, search_request)

        return {
            "files": files,
            "limit": limit,
            "offset": offset,
            "total": len(files),  # Simple implementation - could be optimized
        }

    except Exception as e:
        logger.exception(f"Failed to list files for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file list",
        ) from e


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    principal: Principal = require_principal_module_dep,
    service: FileProcessingService = get_file_processing_service_dep,
):
    """Download a file securely.

    Only allows download of files owned by the current user.
    Returns the file content with appropriate headers for download.
    """
    try:
        import io

        from fastapi.responses import StreamingResponse

        user_id = get_principal_id(principal)

        # Get file metadata and verify ownership
        file_info = await service.get_file(file_id, user_id)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied",
            )

        # Get file content
        file_content = await service.get_file_content(file_id, user_id)
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File content not found",
            )

        # Create streaming response
        _file_stream = io.BytesIO(file_content)

        headers = {
            "Content-Disposition": (
                f'attachment; filename="{file_info.original_filename}"'
            ),
            "Content-Type": file_info.mime_type,
        }

        logger.info(f"File {file_id} downloaded by user {user_id}")

        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=file_info.mime_type,
            headers=headers,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to download file {file_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file",
        ) from e


@router.get("/trips/{trip_id}/attachments")
async def list_trip_attachments(
    trip_id: str,
    principal: Principal = require_principal_module_dep,
    service: FileProcessingService = get_file_processing_service_dep,
    trip_service: TripService = get_trip_service_dep,
    limit: int = 50,
    offset: int = 0,
):
    """List all attachments for a specific trip.

    Only returns attachments for trips the user has access to.

    Security features:
    - Trip access verification (owner or collaborator)
    - Audit logging for access attempts
    - Authorization error handling
    """
    try:
        user_id = get_principal_id(principal)

        # Verify user has access to the trip
        trip = await trip_service.get_trip(trip_id=trip_id, user_id=user_id)
        if not trip:
            # Log unauthorized access attempt
            await audit_security_event(
                event_type=AuditEventType.ACCESS_DENIED,
                severity=AuditSeverity.MEDIUM,
                message=f"Trip access denied for user {user_id} to trip {trip_id}",
                actor_id=user_id,
                ip_address="unknown",  # Could be extracted from request
                target_resource=f"trip_attachments:{trip_id}",
                resource_type="trip_attachments",
                resource_id=trip_id,
                action="list_attachments",
                reason="trip_not_found_or_access_denied",
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found or access denied",
            )

        # Log successful access
        await audit_security_event(
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.LOW,
            message=f"Trip attachments accessed for trip {trip_id}",
            actor_id=user_id,
            ip_address="unknown",
            target_resource=f"trip_attachments:{trip_id}",
            resource_type="trip_attachments",
            resource_id=trip_id,
            action="list_attachments",
            trip_title=trip.title,
        )

        # Create search request filtered by trip
        search_request = FileSearchRequest(
            limit=limit,
            offset=offset,
            filters={"trip_id": trip_id},
        )

        files = await service.search_files(user_id, search_request)

        logger.info(
            f"Listed {len(files)} attachments for trip {trip_id} by user {user_id}"
        )

        return {
            "trip_id": trip_id,
            "files": files,
            "limit": limit,
            "offset": offset,
            "total": len(files),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to list trip attachments for trip {trip_id}")

        # Log system error
        await audit_security_event(
            event_type=AuditEventType.SYSTEM_ERROR,
            severity=AuditSeverity.HIGH,
            message=f"System error accessing trip attachments for trip {trip_id}",
            actor_id=user_id,
            ip_address="unknown",
            target_resource=f"trip_attachments:{trip_id}",
            resource_type="trip_attachments",
            resource_id=trip_id,
            action="list_attachments",
            error=str(e),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trip attachments",
        ) from e
