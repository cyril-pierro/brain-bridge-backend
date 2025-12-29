from fastapi import Request, responses, exceptions
from pydantic import ValidationError
from typing import Union
from sqlalchemy.exc import IntegrityError, DBAPIError
from error import ServerError


def value_error_handler(request: Request, exc: ValueError) -> responses.JSONResponse:
    return responses.JSONResponse(
        status_code=400,
        content={"message": exc.args[0]}
    )


def validation_error_handler(
    request: Request, exec: Union[ValidationError, exceptions.RequestValidationError]
) -> responses.JSONResponse:
    """Validation Error Handler

    This method is serves a custom error handler
    for all validation errors raised by pydantic
    """
    error = exec.errors()[0]
    field = error.get("loc")[-1]
    message = error.get("msg")

    error_msg = f"Invalid {field}: {message}"
    return responses.JSONResponse(
        status_code=422, content={"message": error_msg}
    )


def validation_http_exceptions_handler(
    request: Request, exec: exceptions.HTTPException
) -> responses.JSONResponse:
    """Validation handler for http exceptions"""
    return responses.JSONResponse(
        status_code=exec.status_code, content={"message": exec.detail}
    )


def db_error_handler(request: Request, exec: Union[IntegrityError, DBAPIError]):
    """Db error handler"""
    # Print the actual database error for logging/debugging
    print(f"Database Error: {exec}")
    print(f"Error details: {exec.args[0] if exec.args else 'No details'}")

    # Return user-friendly message that doesn't reveal database details
    user_msg = "An internal error occurred. Please try again or contact support."

    return responses.JSONResponse(
        status_code=500, content={"message": user_msg}
    )


def server_error_handler(request: Request, exec: ServerError) -> responses.JSONResponse:
    """Server error handler"""
    return responses.JSONResponse(
        status_code=exec.status_code,
        content={"message": str(exec.msg)}
    )
