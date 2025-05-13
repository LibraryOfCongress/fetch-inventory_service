import traceback

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.logger import inventory_logger
from app.config.config import get_settings

# Custom exception classes


class BadRequest(HTTPException):
    def __init__(self, detail: str = "Bad Request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class MethodNotAllowed(HTTPException):
    def __init__(self, detail: str = "Method Not Allowed"):
        super().__init__(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail=detail)


class NotFound(HTTPException):
    def __init__(self, detail: str = "Not Found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ValidationException(HTTPException):
    def __init__(self, detail: str = "Validation Error"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )


class InternalServerError(HTTPException):
    def __init__(self, detail: str = "Internal Server Error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


class NotAuthorized(HTTPException):
    def __init__(self, detail: str = "Not Authorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class Forbidden(HTTPException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


# Exception handlers
async def bad_request_exception_handler(request: Request, exc: BadRequest):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.detail or "Bad Request"},
    )

async def method_not_allowed_exception_handler(request: Request, exc: MethodNotAllowed):
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content={"detail": exc.detail or "Method Not Allowed"},
    )

async def not_found_exception_handler(request: Request, exc: NotFound):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.detail or "Not Found"},
    )


async def validation_exception_handler(request: Request, exc: ValidationException):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.detail or "Validation Error"},
    )


async def internal_server_error_exception_handler(
    request: Request, exc: InternalServerError
):
    """
    Lower level exceptions occur before CORSMiddleware.
    It's necessary to attach cross-origin-headers
    directly on this exception handler.
    If you wish to obscure internal server exceptions,
    simply remove the response headers from this method,
    and browser security will only return the response code.
    """
    inventory_logger.disabled = False
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    inventory_logger.warning(f"Unhandled exception at {request.url}:\n{tb}")
    sanitized_client_version = traceback.format_exception_only(type(exc), exc)[-1].strip()
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(sanitized_client_version) or "Internal Server Error"},
    )
    response.headers["Access-Control-Allow-Origin"] = f"{get_settings().VUE_HOST}"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Lower level exceptions occur before CORSMiddleware.
    It's necessary to attach cross-origin-headers
    directly on this exception handler.
    If you wish to obscure internal server exceptions,
    simply remove the response headers from this method,
    and browser security will only return the response code.
    """
    inventory_logger.disabled = False
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    inventory_logger.warning(f"Unhandled exception at {request.url}:\n{tb}")
    sanitized_client_version = traceback.format_exception_only(type(exc), exc)[-1].strip()
    response = JSONResponse(
        # status_code=status.HTTP_418_IM_A_TEAPOT,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(sanitized_client_version) or "FETCH Server Error"}
    )
    response.headers["Access-Control-Allow-Origin"] = f"{get_settings().VUE_HOST}"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


async def not_authorized_exception_handler(request: Request, exc: NotAuthorized):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": exc.detail or "Not Authorized"},
    )


async def forbidden_exception_handler(request: Request, exc: Forbidden):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.detail or "Forbidden"},
    )
