import sqltap

from fastapi import APIRouter
from starlette.responses import HTMLResponse
from app.profiling import profiler, USE_PROFILER

router = APIRouter(
    prefix="/profile",
    tags=["profiling"],
)


@router.get("/", response_class=HTMLResponse)
async def profile_report():
    """Serve the SQLTap profiling report as HTML."""
    # global profiler
    if not USE_PROFILER or profiler is None:
        return HTMLResponse("<h1>Profiling is disabled</h1>", status_code=403)
    
    stats = profiler.collect()
    html_report = sqltap.report(stats, "html")  # Generate HTML report
    return HTMLResponse(html_report)
