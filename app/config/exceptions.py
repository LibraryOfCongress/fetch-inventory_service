from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


# Custom exception classes


class BadRequest(HTTPException):
    def __init__(self, detail: str = "Bad Request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


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
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": exc.detail or "Internal Server Error"},
    )


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
