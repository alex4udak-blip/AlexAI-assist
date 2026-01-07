"""Security utilities."""

import re
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException
from jose import jwt
from passlib.context import CryptContext

from src.core.config import settings
from src.core.logging import get_logger, log_security_event

logger = get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Session ID validation pattern (UUID format or alphanumeric with max length)
SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt: str = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return cast(bool, pwd_context.verify(plain_password, hashed_password))


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return cast(str, pwd_context.hash(password))


def validate_session_id(session_id: str) -> str:
    """
    Validate and sanitize session_id to prevent session forgery.

    Args:
        session_id: The session ID to validate

    Returns:
        The validated session ID

    Raises:
        HTTPException: If session_id is invalid

    Security Notes:
        - This function validates the FORMAT of session_id only
        - It does NOT validate session OWNERSHIP (requires user authentication)
        - RECOMMENDATION: Implement proper user authentication with session ownership
        - Future improvement: Add user_id validation to ensure users can only access their sessions
    """
    if not session_id:
        log_security_event(
            logger,
            "Session validation failed: missing session ID",
            details={"reason": "empty_session_id"},
        )
        raise HTTPException(
            status_code=400,
            detail="Session ID is required"
        )

    # Strip whitespace and convert to lowercase for consistency
    session_id = session_id.strip()

    # Check for empty string after stripping
    if not session_id:
        log_security_event(
            logger,
            "Session validation failed: empty session ID after stripping",
            details={"reason": "empty_after_strip"},
        )
        raise HTTPException(
            status_code=400,
            detail="Session ID cannot be empty"
        )

    # Validate against pattern (alphanumeric, underscores, hyphens only)
    if not SESSION_ID_PATTERN.match(session_id):
        log_security_event(
            logger,
            "Session validation failed: invalid format",
            details={
                "reason": "invalid_format",
                "session_id_length": len(session_id),
            },
        )
        raise HTTPException(
            status_code=400,
            detail="Invalid session ID format. Only alphanumeric characters, underscores, and hyphens are allowed (max 64 chars)"
        )

    # Check for SQL injection attempts
    sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "UNION", "--", ";", "/*", "*/"]
    session_id_upper = session_id.upper()
    for keyword in sql_keywords:
        if keyword in session_id_upper:
            log_security_event(
                logger,
                "Potential SQL injection attempt detected in session ID",
                details={
                    "reason": "sql_injection_attempt",
                    "keyword_detected": keyword,
                },
                level="ERROR",
            )
            raise HTTPException(
                status_code=400,
                detail="Invalid session ID format"
            )

    return session_id


def is_valid_uuid_format(value: str) -> bool:
    """
    Check if a string is in valid UUID format.

    Args:
        value: String to check

    Returns:
        True if valid UUID format, False otherwise
    """
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def validate_session_ownership(
    session_id: str,
    user_id: str | None = None,
) -> None:
    """
    Validate that a user has access to a specific session.

    Args:
        session_id: The session ID to validate
        user_id: The user ID attempting to access the session (optional for now)

    Raises:
        HTTPException: If validation fails

    Security Notes:
        - IMPORTANT: This function is a placeholder for future implementation
        - Currently, there is NO user authentication system in place
        - TODO: Implement user authentication and session ownership tracking
        - TODO: Store session_id -> user_id mapping in database
        - TODO: Verify user_id matches session owner before allowing access

    Current Behavior:
        - Only validates session_id format
        - Does NOT enforce ownership (no user model exists yet)
    """
    # Validate format
    validate_session_id(session_id)

    # TODO: Implement user authentication
    # When user authentication is implemented:
    # 1. Check if user_id is provided (from JWT token or session)
    # 2. Query database to verify session belongs to user
    # 3. Raise HTTPException(403) if ownership check fails
    #
    # Example future implementation:
    # if user_id:
    #     session = await db.query(Session).filter(
    #         Session.id == session_id,
    #         Session.user_id == user_id
    #     ).first()
    #     if not session:
    #         raise HTTPException(
    #             status_code=403,
    #             detail="Access denied: Session not found or not owned by user"
    #         )

    pass
