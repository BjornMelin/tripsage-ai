"""File attachment router for TripSage API.

This module provides endpoints for secure file uploads, processing, and AI analysis
of travel documents, following KISS principles and security best practices.
"""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from tripsage.api.core.dependencies import (
    FileProcessingServiceDep,
    RequiredPrincipalDep,
    TripServiceDep,
    get_principal_id,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.attachments import (
    BatchUploadResponse,
    DeleteFileResponse,
    FileListResponse,
    FileMetadataResponse,
    FileUploadResponse,
)
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditSeverity,
    audit_security_event,
)
from tripsage_core.services.business.file_processing_service import (
    FileSearchRequest,
    FileUploadRequest,
)

# Trip service is injected via dependencies module
from tripsage_core.utils.file_utils import MAX_SESSION_SIZE, validate_file


logger = logging.getLogger(__name__)

router = APIRouter()

# File configuration now imported from centralized config

# Module-level dependencies to avoid B008 warnings
require_principal_module_dep = RequiredPrincipalDep

# Module-level dependency for file uploads
file_upload_dep = File(...)
files_upload_dep = File(...)


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    service: FileProcessingServiceDep,
    file: UploadFile = file_upload_dep,
    principal: Principal = require_principal_module_dep,  # type: ignore  # type: ignore[assignment]
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
            filename=file.filename or "uploaded_file",
            content=content,
            auto_analyze=True,
        )

        # Process file
        result = await service.upload_file(user_id, upload_request)

        logger.info(
            "File uploaded successfully: %s (%s bytes) for user %s",
            file.filename,
            result.file_size,
            user_id,
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
        logger.exception("File processing failed for %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File processing failed",
        ) from e


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_files_batch(
    service: FileProcessingServiceDep,
    files: list[UploadFile] = files_upload_dep,
    principal: Principal = require_principal_module_dep,  # type: ignore
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
                errors.append(f"{file.filename}: {validation_result.error_message}")  # type: ignore[unknown-member-type]
                continue

            # Read file content
            content = await file.read()

            # Create upload request
            upload_request = FileUploadRequest(
                filename=file.filename or "uploaded_file",
                content=content,
                auto_analyze=True,
            )

            # Process file
            result = await service.upload_file(user_id, upload_request)
            processed_files.append(  # type: ignore[unknown-member-type]
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
            logger.exception("Failed to process file %s", file.filename)
            errors.append(f"{file.filename}: Processing failed")  # type: ignore[unknown-member-type]

    if errors and not processed_files:
        # All files failed
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"All files failed validation/processing: {'; '.join(errors)}",  # type: ignore[unknown-argument-type]
        )

    if errors:
        # Some files failed - log warnings but return successful ones
        logger.warning("Some files failed processing: %s", "; ".join(errors))  # type: ignore[unknown-argument-type]

    logger.info(
        "Batch upload completed: %s/%s files processed for user %s",
        len(processed_files),  # type: ignore[unknown-argument-type]
        len(files),
        user_id,
    )

    return BatchUploadResponse(
        files=processed_files,  # type: ignore[unknown-argument-type]
        total_files=len(processed_files),  # type: ignore[unknown-argument-type]
        total_size=sum(f.file_size for f in processed_files),  # type: ignore[unknown-argument-type,unknown-variable-type]
    )


@router.get("/files/{file_id}", response_model=FileMetadataResponse)
async def get_file_metadata(
    file_id: str,
    service: FileProcessingServiceDep,
    principal: Principal = require_principal_module_dep,  # type: ignore
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
        logger.exception("Failed to get file info for %s", file_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file information",
        ) from e


@router.delete("/files/{file_id}", response_model=DeleteFileResponse)
async def delete_file(
    file_id: str,
    service: FileProcessingServiceDep,
    principal: Principal = require_principal_module_dep,  # type: ignore
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

        logger.info("File %s deleted by user %s", file_id, user_id)
        return DeleteFileResponse(message="File deleted successfully", file_id=file_id)

    except Exception as e:
        logger.exception("Failed to delete file %s", file_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file",
        ) from e


@router.get("/files", response_model=FileListResponse)
async def list_files(
    service: FileProcessingServiceDep,
    principal: Principal = require_principal_module_dep,  # type: ignore
    limit: int = 50,
    offset: int = 0,
):
    """List files uploaded by the current user with pagination."""
    user_id = "unknown"
    try:
        user_id = get_principal_id(principal)

        # Create search request with basic pagination
        search_request = FileSearchRequest(limit=limit, offset=offset)

        raw_files = await service.search_files(user_id, search_request)

        # Adapt service results to API schema
        adapted: list[FileMetadataResponse] = []
        for f in raw_files:
            try:
                file_id = getattr(f, "id", getattr(f, "file_id", ""))
                filename = getattr(f, "original_filename", getattr(f, "filename", ""))
                file_size = int(getattr(f, "file_size", 0) or 0)
                mime_type = getattr(f, "mime_type", "")
                status_val = getattr(
                    getattr(f, "processing_status", None), "value", None
                )
                processing_status = status_val or str(
                    getattr(f, "processing_status", "unknown")
                )
                created_at = getattr(f, "created_at", None)
                analysis_summary = getattr(f, "analysis_summary", None)

                adapted.append(  # type: ignore[unknown-member-type]
                    FileMetadataResponse(
                        file_id=file_id,
                        filename=filename,
                        file_size=file_size,
                        mime_type=mime_type,
                        processing_status=processing_status,
                        created_at=(
                            created_at.isoformat()
                            if (
                                created_at is not None
                                and hasattr(created_at, "isoformat")
                            )
                            else None
                        ),
                        analysis_summary=analysis_summary,
                    )
                )
            except Exception:
                logger.exception("Failed to adapt file metadata for response")
                continue

        return FileListResponse(
            files=adapted, limit=limit, offset=offset, total=len(adapted)
        )

    except Exception as e:
        logger.exception("Failed to list files for user %s", user_id)  # type: ignore[possibly-unbound-variable]
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file list",
        ) from e


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    service: FileProcessingServiceDep,
    principal: Principal = require_principal_module_dep,  # type: ignore
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

        logger.info("File %s downloaded by user %s", file_id, user_id)

        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=file_info.mime_type,
            headers=headers,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to download file %s", file_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file",
        ) from e


@router.get("/trips/{trip_id}/attachments")
async def list_trip_attachments(
    trip_id: str,
    service: FileProcessingServiceDep,
    trip_service: TripServiceDep,
    *,
    principal: Principal = require_principal_module_dep,  # type: ignore
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
    user_id = "unknown"
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
            trip_id=trip_id,
        )

        files = await service.search_files(user_id, search_request)

        logger.info(
            "Listed %s attachments for trip %s by user %s", len(files), trip_id, user_id
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
        logger.exception("Failed to list trip attachments for trip %s", trip_id)

        # Log system error
        await audit_security_event(
            event_type=AuditEventType.SYSTEM_ERROR,
            severity=AuditSeverity.HIGH,
            message=f"System error accessing trip attachments for trip {trip_id}",
            actor_id=user_id,  # type: ignore[possibly-unbound-variable]
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
