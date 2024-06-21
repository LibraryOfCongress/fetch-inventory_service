import time
from fastapi import Request
from app.logger import inventory_logger, data_activity_logger


async def log_middleware(request: Request, call_next):
    start = time.time()
    # Something explicitly disables logger in middleware
    inventory_logger.disabled = False
    data_activity_logger.disabled = False

    response = await call_next(request)

    # Ensure as accurate as possible IP
    x_forwarded_for = request.headers.get('X-forwarded-For')
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.client.host

    process_time = time.time() - start

    # Output to stream
    request_log_dict = {
        'url': request.url.path,
        'method': request.method,
        'response_status': response.status_code,
        'process_time': process_time
    }

    # Output to log file
    security_log_dict = {
        'ip': client_ip,
        'user-agent': request.headers.get("user-agent", "unknown"),
        'referer': request.headers.get("referer", "unknown"),
        'headers': dict(request.headers),
        'query-params': dict(request.query_params),
        'url': request.url.path,
        'method': request.method,
        'response_status': response.status_code,
        'process_time': process_time
    }

    if response.status_code > 399:
        inventory_logger.warn(request_log_dict)
        data_activity_logger.warn(security_log_dict)
    else:
        inventory_logger.info(request_log_dict)
        data_activity_logger.info(security_log_dict)
    return response
