import time, jwt
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.security import OAuth2PasswordBearer
from app.logger import inventory_logger, data_activity_logger


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class JWTMiddleware(BaseHTTPMiddleware):
    """
    This middleware is responsible for enforcing Auth token checks.
    This middleware is responsible for capturing logs
    """
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        # Something explicitly disables logger in middleware
        inventory_logger.disabled = False
        data_activity_logger.disabled = False
        # Ensure as accurate as possible IP
        x_forwarded_for = request.headers.get('X-forwarded-For')
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.client.host

        #debug testing
        x_forwarded_proto = request.headers.get('X-Forwarded-Proto', 'http')
        x_forwarded_host = request.headers.get('X-Forwarded-Host', request.url.hostname)
        if x_forwarded_proto:
            request.url.scheme = x_forwarded_proto
        if x_forwarded_host:
            request.url.hostname = x_forwarded_host

        process_time = time.time() - start

        # Get token from Authorization header
        token = None
        decoded_token = None
        fetch_user = 'unkown'
        auth_header = request.headers.get("authorization")
        if auth_header:
            token = auth_header.split("Bearer ")[1]
            decoded_token = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
            fetch_user = decoded_token.get('email')

        # Exclude /auth endpoints from token validation
        if request.url.path.startswith("/auth"):
            response = await call_next(request)
        elif request.url.path.startswith("/status"):
            response = await call_next(request)
        elif not token:
            response = JSONResponse(status_code=401, content={"detail": "Not Authorized"})
        else:
            # Check if token is expired
            token_exp = decoded_token.get('exp')
            token_exp_datetime = datetime.utcfromtimestamp(token_exp)
            if token_exp_datetime < datetime.utcnow():
                response = JSONResponse(status_code=401, content={"detail": "Token Expired"})
            else:
                # Everything's good
                response = await call_next(request)

        request_log_dict = {
            'url': request.url.path,
            'method': request.method,
            'response_status': response.status_code,
            'process_time': process_time
        }
        security_log_dict = {
            'ip': client_ip,
            'user': fetch_user,
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
