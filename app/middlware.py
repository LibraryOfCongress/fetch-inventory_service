import time
from fastapi import Request
from app.logger import inventory_logger


async def log_middleware(request: Request, call_next):
    start = time.time()
    # Something explicitly disables logger in middleware
    inventory_logger.disabled = False

    response = await call_next(request)

    process_time = time.time() - start
    request_log_dict = {
        'url': request.url.path,
        'method': request.method,
        'response_status': response.status_code,
        'process_time': process_time
    }
    if response.status_code > 399:
        inventory_logger.warn(request_log_dict)
    else:
        inventory_logger.info(request_log_dict)
    return response
