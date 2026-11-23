"""Turn database errors into HTTP errors with meaningful status codes."""

import logging

import httpx
from fastapi import HTTPException
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)

# SQLSTATE codes raised by our database functions (see
# supabase/migrations/20261122170200_reservations_payments.sql) or by
# PostgreSQL itself, and the HTTP status each one maps to.
DB_ERROR_STATUS = {
    "28000": 401,  # not signed in
    "42501": 403,  # permission denied (row level security / privileges)
    "P0002": 404,  # machine or reservation not found, or not yours
    "22023": 422,  # invalid input, e.g. a start time in the past
    "LM001": 422,  # machine inactive or out of service
    "23514": 422,  # CHECK constraint violated
    "23P01": 409,  # time slot overlaps another active reservation
    "LM002": 409,  # reservation is in a state that does not allow the action
    "23505": 409,  # unique constraint violated
}


def db_error(exc: Exception, fallback: str) -> HTTPException:
    """Build the HTTPException to raise for an error from Supabase.

    Known database error codes keep the database's message, which is written
    for end users. Anything else is logged and reported with a generic message
    so internal details are not exposed.
    """
    if isinstance(exc, APIError) and exc.code in DB_ERROR_STATUS:
        return HTTPException(
            status_code=DB_ERROR_STATUS[exc.code],
            detail=exc.message or fallback,
        )

    if isinstance(exc, httpx.HTTPError):
        logger.error("%s: database unreachable (%s)", fallback, type(exc).__name__)
        return HTTPException(status_code=503, detail=f"{fallback}: database unavailable")

    code = getattr(exc, "code", None)
    logger.error("%s: unexpected database error (code=%s)", fallback, code)
    return HTTPException(status_code=500, detail=fallback)
