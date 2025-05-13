from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.database.session import get_session
from sqlmodel import Session


router = APIRouter(
    prefix="/status",
    tags=["status"],
)

@router.get("/")
def get_api_status(session: Session = Depends(get_session)) -> list:
    """
    This endpoint simply returns a 200 OK to show the API is running.
    Auth middleware allows consumption without a Bearer token
    """
    return JSONResponse(status_code=200, content={"detail": "OK"})
