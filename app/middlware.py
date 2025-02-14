import time, jwt#, sqltap
from anyio import to_thread
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.security import OAuth2PasswordBearer
from app.logger import inventory_logger, data_activity_logger, security_log_route_filter
from app.config.config import get_settings
from app.database.session import get_session, session_manager
from app.models.users import User
from app.utilities import set_session_to_request, is_tz_naive
from app.profiling import profiler, USE_PROFILER

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

        process_time = time.time() - start

        # Get token from Authorization header
        token = None
        decoded_token = None
        fetch_user = 'unknown'
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
            if get_settings().APP_ENVIRONMENT not in ["debug", "local", "develop", "test"]:
                response = JSONResponse(status_code=401, content={"detail": "Not Authorized"})
            else:
                response = await call_next(request)
        else:
            # Check if token is expired
            # token_exp = decoded_token.get('exp')
            # token_exp_datetime = datetime.utcfromtimestamp(token_exp)
            # from user table
            # with get_session() as session:
            with session_manager() as session:
                # session here
                user_object = session.query(User).filter(User.email == fetch_user).first()
                token_exp_datetime = user_object.fetch_auth_expiration
                if token_exp_datetime < datetime.now(timezone.utc):
                    if get_settings().APP_ENVIRONMENT not in ["local", "develop", "test"]:
                        response = JSONResponse(status_code=401, content={"detail": "Token Expired"})
                    else:
                        # request = await to_thread.run_sync(set_session_to_request, request, fetch_user)
                        request = set_session_to_request(request, fetch_user)
                        response = await call_next(request)
                else:
                    # Everything's good
                    # refresh exp and pass through
                    user_object.fetch_auth_expiration = datetime.now(timezone.utc) + timedelta(minutes=15)
                    session.add(user_object)
                    # session.commit(user_object)
                    session.commit()
                    session.refresh(user_object)
                    # request = await to_thread.run_sync(set_session_to_request, request, fetch_user)
                    request = set_session_to_request(request, fetch_user)
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

        if response.status_code == (401 or 403):
            # always log 401 & 403 regardless of route
            data_activity_logger.warn(security_log_dict)
        else:
            # else log on routes in filter
            if any(request.url.path.startswith(route) for route in security_log_route_filter):
                data_activity_logger.info(security_log_dict)

        return response


# # Middleware query profiling
# class SQLProfilerMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         if USE_PROFILER:
#             profiler = sqltap.start() # resets profiler per request
#         response = await call_next(request)
#         return response
