import time, jwt#, sqltap
# from anyio import to_thread
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
            # health check doesn't have scope['client'] for client context
            client_ip = request.client.host if request.client else "unknown"
            # client_ip = request.client.host

        process_time = time.time() - start

        # Get token from cookies first (HttpOnly secure pattern), fallback to Authorization header
        token = request.cookies.get("fetch_auth_token")
        decoded_token = None
        fetch_user = 'unknown'

        if not token:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split("Bearer ")[1]

        if token:
            try:
                decoded_token = jwt.decode(token, get_settings().JWT_SECRET_KEY, algorithms=['HS256'])
                fetch_user = decoded_token.get('email', 'unknown')
            except jwt.ExpiredSignatureError:
                # Let it pass here, we handle expiration later in the flow vs the database if needed,
                # or we can reject it right now securely without throwing a 500.
                if get_settings().APP_ENVIRONMENT not in ["debug", "local", "develop", "test"] and not request.url.path.startswith("/auth") and not request.url.path.startswith("/status"):
                    return JSONResponse(status_code=401, content={"detail": "Token Expired"})
                token = None # Invalid token for strict environments
            except jwt.PyJWTError:
                # Catch malformed/invalid tokens gracefully (Prevents 500 Error DoS)
                if get_settings().APP_ENVIRONMENT not in ["debug", "local", "develop", "test"] and not request.url.path.startswith("/auth") and not request.url.path.startswith("/status"):
                    return JSONResponse(status_code=401, content={"detail": "Invalid Token"})
                token = None

        # Exclude /auth endpoints from token validation
        if request.url.path.startswith("/auth"):
            response = await call_next(request)
        elif request.url.path.startswith("/status"):
            response = await call_next(request)
        elif not token or not decoded_token:
            if get_settings().APP_ENVIRONMENT not in ["debug", "local", "develop", "test"]:
                response = JSONResponse(status_code=401, content={"detail": "Not Authorized"})
            else:
                response = await call_next(request)
        else:
            # Do all auth DB work in a short-lived session and CLOSE it before
            # call_next. Previously the session_manager block wrapped call_next, so
            # this connection stayed checked out for the whole request; on a long
            # request (e.g. bulk upload) the idle connection to the external DB gets
            # dropped and session cleanup then raises "SSL connection closed
            # unexpectedly" -> 500. The handler audits via its own session
            # (get_session re-applies audit_info), so nothing here needs to stay open
            # during call_next.
            token_expired_reject = False
            refreshed_cookie = None  # (token, is_secure) -> set on the response after call_next
            with session_manager() as session:
                user_object = session.query(User).filter(User.email == fetch_user).first()
                audit_info = {
                    "name": f"{user_object.first_name} {user_object.last_name}",
                    "id": user_object.id,
                }
                token_exp_datetime = user_object.fetch_auth_expiration
                if token_exp_datetime < datetime.now(timezone.utc):
                    if get_settings().APP_ENVIRONMENT not in ["debug", "local", "test"]:
                        token_expired_reject = True
                    else:
                        # request = set_session_to_request(request, fetch_user)
                        request = await set_session_to_request(request, session, audit_info)
                else:
                    # Everything's good
                    # refresh exp and pass through (sliding window)
                    new_exp = datetime.now(timezone.utc) + timedelta(minutes=15)
                    user_object.fetch_auth_expiration = new_exp
                    session.add(user_object)
                    session.commit()
                    session.refresh(user_object)
                    request = await set_session_to_request(request, session, audit_info)

                    # Re-issue JWT with refreshed exp claim (sliding window).
                    # Read user_object fields here while the session is still open.
                    refreshed_payload = {
                        "user_id": user_object.id,
                        "first_name": user_object.first_name,
                        "last_name": user_object.last_name,
                        "email": user_object.email,
                        "exp": new_exp
                    }
                    refreshed_token = jwt.encode(refreshed_payload, get_settings().JWT_SECRET_KEY, algorithm='HS256')
                    is_secure = get_settings().APP_ENVIRONMENT not in ["debug", "local"]
                    refreshed_cookie = (refreshed_token, is_secure)
            # --- session is now closed; no DB connection held during call_next ---

            if token_expired_reject:
                response = JSONResponse(status_code=401, content={"detail": "Token Expired"})
            else:
                response = await call_next(request)
                if refreshed_cookie is not None:
                    token_value, secure_flag = refreshed_cookie
                    response.set_cookie(
                        key="fetch_auth_token",
                        value=token_value,
                        httponly=True,
                        secure=secure_flag,
                        samesite="lax",
                        max_age=900
                    )
        request_log_dict = {
            'url': request.url.path,
            'method': request.method,
            'response_status': response.status_code,
            'process_time': process_time
        }
        # Sanitize headers to prevent token/cookie logging (NIST AU-9)
        sensitive_headers = {'authorization', 'cookie', 'set-cookie'}
        sanitized_headers = {
            k: "***REDACTED***" if k.lower() in sensitive_headers else v
            for k, v in request.headers.items()
        }

        # Sanitize query parameters to prevent URL-token logging
        sensitive_params = {'token', 'code', 'state', 'password'}
        sanitized_query_params = {
            k: "***REDACTED***" if k.lower() in sensitive_params else v
            for k, v in request.query_params.items()
        }

        security_log_dict = {
            'ip': client_ip,
            'user': fetch_user,
            'user-agent': request.headers.get("user-agent", "unknown"),
            'referer': request.headers.get("referer", "unknown"),
            'headers': sanitized_headers,
            'query-params': sanitized_query_params,
            'url': request.url.path,
            'method': request.method,
            'response_status': response.status_code,
            'process_time': process_time
        }

        if response.status_code == (401 or 403):
            # always log 401 & 403 regardless of route
            data_activity_logger.warning(security_log_dict)
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
