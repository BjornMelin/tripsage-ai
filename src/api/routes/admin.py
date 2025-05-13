"""
Admin routes for TripSage API.

This module provides admin-only routes for database management and system configuration.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.api.auth import User, get_current_active_user
from src.api.database import get_repository, get_user_repository
from src.db.migrations import run_migrations
from src.db.repositories.user import UserRepository

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


class MigrationResponse(BaseModel):
    """Response model for migration operations."""

    message: str
    succeeded: int
    failed: int


class MigrationOptions(BaseModel):
    """Options for running migrations."""

    up_to: str = None
    dry_run: bool = False


async def validate_admin(
    current_user: User = None,
    user_repo: UserRepository = None,
):
    """
    Validate that the current user is an admin.

    Args:
        current_user: The current user
        user_repo: The user repository

    Returns:
        The current user if they are an admin

    Raises:
        HTTPException: If the user is not an admin
    """
    if current_user is None:
        current_user = await get_current_active_user()
    if user_repo is None:
        user_repo = get_repository(get_user_repository)()

    user = await user_repo.get_by_id(int(current_user.id))
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.post("/migrations/run", response_model=MigrationResponse)
async def run_migrations_route(
    options: MigrationOptions,
    _: User = None,
):
    """
    Run database migrations.

    Args:
        options: Migration options
        _: Current admin user (from dependency)

    Returns:
        Migration response with migration results
    """
    if _ is None:
        _ = await validate_admin()

    # Run migrations with service role key
    succeeded, failed = await run_migrations(
        service_key=True,
        up_to=options.up_to,
        dry_run=options.dry_run,
    )

    # Create response message
    if options.dry_run:
        message = f"Dry run: would apply {succeeded} migrations"
    elif failed > 0:
        message = f"Migrations completed with errors: {failed} failed, {succeeded} succeeded"
    elif succeeded == 0:
        message = "No migrations were applied"
    else:
        message = f"Successfully applied {succeeded} migrations"

    return MigrationResponse(
        message=message,
        succeeded=succeeded,
        failed=failed,
    )


@router.get("/migrations/status", response_model=MigrationResponse)
async def get_migrations_status(_: User = None):
    """
    Get status of migrations.

    Args:
        _: Current admin user (from dependency)

    Returns:
        Migration status
    """
    if _ is None:
        _ = await validate_admin()

    # Get list of migrations that would be applied in a dry run
    succeeded, failed = await run_migrations(
        service_key=True,
        dry_run=True,
    )

    if succeeded == 0:
        message = "Database is up to date, no pending migrations"
    else:
        message = f"There are {succeeded} pending migrations"

    return MigrationResponse(
        message=message,
        succeeded=succeeded,
        failed=failed,
    )