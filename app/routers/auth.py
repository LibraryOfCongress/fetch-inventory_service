# /code/app/routers/auth.py - REFACRORED TO SQLALCHEMY V2

import json, jwt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, HTTPException, Response, status, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from app.config.config import get_settings
from app.models.users import User
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select     # select is imported from sqlalchemy now
from app.database.session import get_session
from app.schemas.auth import LegacyUserInput
from app.config.exceptions import NotFound
from app.filter_params import AuthFilterParams
from app.auth.dependencies import get_current_user_with_permissions

from urllib.parse import urlparse
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings


router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)

def load_saml_settings():

    # Optimize - idp xml's should move to env, copy in one per build
    match get_settings().APP_ENVIRONMENT:
        case "debug":
            saml_config_file = "app/saml/config/local_saml_config.json"
            with open(saml_config_file) as f:
                settings = json.load(f)
            with open("app/saml/local/cert.pem", "r") as cert_file:
                certificate = cert_file.read()
            with open("app/saml/local/key.pem", "r") as key_file:
                private_key = key_file.read()
            settings['sp']['x509cert'] = certificate
            settings['sp']['privateKey'] = private_key
        case "local":
            saml_config_file = "app/saml/config/local_saml_config.json"
            with open(saml_config_file) as f:
                settings = json.load(f)
            with open("app/saml/local/cert.pem", "r") as cert_file:
                certificate = cert_file.read()
            with open("app/saml/local/key.pem", "r") as key_file:
                private_key = key_file.read()
            settings['sp']['x509cert'] = certificate
            settings['sp']['privateKey'] = private_key
        case "develop":
            saml_config_file = "app/saml/config/dev_saml_config.json"
            with open(saml_config_file) as f:
                settings = json.load(f)
            # with open("app/saml/develop/cert.pem", "r") as cert_file:
            #     certificate = cert_file.read()
            # with open("app/saml/develop/key.pem", "r") as key_file:
            #     private_key = key_file.read()
            # settings['sp']['x509cert'] = certificate
            # settings['sp']['privateKey'] = private_key
        case "test":
            saml_config_file = "app/saml/config/test_saml_config.json"
            with open(saml_config_file) as f:
                settings = json.load(f)
            # with open("app/saml/test/cert.pem", "r") as cert_file:
            #     certificate = cert_file.read()
            # with open("app/saml/test/key.pem", "r") as key_file:
            #     private_key = key_file.read()
            # settings['sp']['x509cert'] = certificate
            # settings['sp']['privateKey'] = private_key
        case "stage":
            saml_config_file = "app/saml/config/stage_saml_config.json"
            with open(saml_config_file) as f:
                settings = json.load(f)
            # with open("app/saml/stage/cert.pem", "r") as cert_file:
            #     certificate = cert_file.read()
            # with open("app/saml/stage/key.pem", "r") as key_file:
            #     private_key = cert_file.read()
            # settings['sp']['x509cert'] = certificate
            # settings['sp']['privateKey'] = private_key
        case "production":
            saml_config_file = "app/saml/config/prod_saml_config.json"
            with open(saml_config_file) as f:
                settings = json.load(f)
            # with open("app/saml/production/cert.pem", "r") as cert_file:
            #     certificate = cert_file.read()
            # with open("app/saml/production/key.pem", "r") as key_file:
            #     private_key = cert_file.read()
            # settings['sp']['x509cert'] = certificate
            # settings['sp']['privateKey'] = private_key
        case _:
            raise Exception(f"No matching saml config for {get_settings().APP_ENVIRONMENT} environment.")

    return settings

def init_saml_auth(req):
    saml_settings = load_saml_settings()
    settings = OneLogin_Saml2_Settings(settings=saml_settings)
    # service provider saml instance
    auth = OneLogin_Saml2_Auth(req, old_settings=settings)
    return auth

def generate_token(user_object, session: Session):
    payload = {
        "user_id": user_object.id,
        "first_name": user_object.first_name,
        "last_name": user_object.last_name,
        "email": user_object.email,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=15)  # NIST IA-11: Cryptographic session expiration
    }
    token = jwt.encode(payload, get_settings().JWT_SECRET_KEY, algorithm="HS256")

    setattr(user_object, "fetch_auth_token", token)
    setattr(user_object, "fetch_auth_expiration", datetime.now(timezone.utc) + timedelta(minutes=15))

    session.add(user_object)
    session.commit()
    session.refresh(user_object)
    return token

async def prepare_fastapi_request(request: Request):
    # Converts FastAPI request to a dict

    #debug testing
    # forwarded_proto = request.headers.get('X-Forwarded-Proto', request.url.scheme)
    forwarded_host = request.headers.get('X-Forwarded-Host')
    if not forwarded_host:
        forwarded_host = request.url.hostname
    forwarded_port = request.headers.get('X-Forwarded-Port')
    if not forwarded_port:
        forwarded_port = request.url.port
    # forwarded_for = request.headers.get('X-Forwarded-For', request.client.host)

    url_data = urlparse(str(request.url))
    # if local, cast 127.0.0.1 to localhost
    acs_host = 'localhost'
    acs_port = url_data.port
    if get_settings().APP_ENVIRONMENT not in ["debug", "local"]:
        # acs_host = request.client.host # this could be an issue
        # acs_port = url_data.port

        #debug testing
        # acs_host = forwarded_host
        acs_host = f"{forwarded_host}/auth/sso/acs"
        acs_port = forwarded_port

    return {
        'http_host': acs_host,
        'script_name': request.scope.get('root_path'),
        'server_port': acs_port,
        'https': 'on',#'on' if url_data.scheme == 'https' else 'off'
        'get_data': request.query_params,
        'post_data': await request.form()
    }

@router.get("/sso/metadata")
async def saml_metadata():
    saml_settings = load_saml_settings()
    settings = OneLogin_Saml2_Settings(
        settings=saml_settings,
        sp_validation_only=True
    )
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)
    if len(errors) > 0:
        raise HTTPException(status_code=500, detail=', '.join(errors))
    return Response(content=metadata, media_type="text/xml")

@router.get("/sso/login/")
async def saml_login(
    request: Request,
    params: AuthFilterParams = Depends()
):
    req = await prepare_fastapi_request(request)
    auth = init_saml_auth(req)

    relay_state = params.preserve_route if params.preserve_route else "/"

    # sso_built_url = auth.login(force_authn=True, return_to=relay_state)
    # force flag disables smart cards, ignores existing sessions on idP
    sso_built_url = auth.login(return_to=relay_state)

    return RedirectResponse(sso_built_url)

@router.post("/sso/acs")
async def saml_acs(request: Request, session: Session = Depends(get_session)):
    req = await prepare_fastapi_request(request)
    auth = init_saml_auth(req)
    auth.process_response()
    errors = auth.get_errors()
    last_error_reason = auth.get_last_error_reason()
    if len(errors) > 0 or not auth.is_authenticated():
        # raise HTTPException(status_code=400, detail=', '.join(errors))
        # temp debug
        raise HTTPException(status_code=400, detail=f"{errors}, last error reason: {last_error_reason}")

    user_info = auth.get_attributes()

    # Get or Create User
    user_email = user_info[
        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress'
    ][0]
    user_first_name = user_info[
        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname'
    ][0]
    user_last_name = user_info[
        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname'
    ][0]
    user_query = select(User).where(User.email==user_email)
    # CRITICAL V2 FIX: session.exec().first() -> session.execute(query).scalars().first()
    user = session.execute(user_query).scalars().first()
    if not user:
        # create user
        user = User(
            email=user_email,
            first_name=user_first_name,
            last_name=user_last_name
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    # Generate token for the user (e.g., JWT)
    token = generate_token(user, session)

    # Retrieve RelayState from 'preserve_route' pass through
    relay_state = req.get('post_data').get('RelayState', "/")

    # Set token as an HttpOnly secure cookie instead of a URL parameter.
    # lstrip the leading slash(es): relay_state is the SPA fullPath (starts with
    # "/"), so f"{VUE_HOST}/{relay_state}" would yield a double slash
    # (host//shelving/123). A leading "//" is parsed by the browser as a
    # protocol-relative URL — the route is lost and it's an open-redirect risk —
    # so normalize to a single-slash path under VUE_HOST.
    response = RedirectResponse(
        url=f"{get_settings().VUE_HOST}/{relay_state.lstrip('/')}",
        status_code=status.HTTP_303_SEE_OTHER,
    )

    # Determine Secure flag based on environment (local might be http)
    is_secure = get_settings().APP_ENVIRONMENT not in ["debug", "local"]

    response.set_cookie(
        key="fetch_auth_token",
        value=token,
        httponly=True,
        secure=is_secure,
        samesite="lax",  # Allows the redirect to send the cookie
        max_age=900,  # 15 minutes
    )

    return response

@router.post("/sso/logout/")
async def sso_logout():
    """Clears the explicit HttpOnly authentication cookie."""
    response = JSONResponse(content={"detail": "Logged out successfully"})
    response.delete_cookie("fetch_auth_token")
    return response

if get_settings().APP_ENVIRONMENT in ['debug', 'local', 'develop', 'test']:
        # Route only available in non prod envs
    @router.post('/legacy/login')
    async def legacy_login(request: Request, legacy_user: LegacyUserInput, session: Session = Depends(get_session)):
        user_query = select(User).where(User.email==legacy_user.email)
        # CRITICAL V2 FIX: session.exec().first() -> session.execute(query).scalars().first()
        user = session.execute(user_query).scalars().first()
        if not user:
            raise NotFound(detail=f"User not found for {legacy_user.email}")

        token = generate_token(user, session)

        response = JSONResponse({"detail": "Login successful"}, status_code=200)

        is_secure = get_settings().APP_ENVIRONMENT not in ["debug", "local"]
        response.set_cookie(
            key="fetch_auth_token",
            value=token,
            httponly=True,
            secure=is_secure,
            samesite="lax",
            max_age=900
        )

        return response

@router.get('/me')
async def get_current_user_profile(user: User = Depends(get_current_user_with_permissions)):
    """
    Returns the profile and permissions of the currently authenticated user.
    Required by the frontend to initialize the User Store via HttpOnly cookies.
    """
    # Build a simplified response mirroring what jwt decoding + users API used to provide
    permissions = []
    if user.groups:
        for group in user.groups:
            if group.permissions:
                for perm in group.permissions:
                    permissions.append(perm.name)

    return {
        "user_id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "default_building_id": user.default_building_id,
        "permissions": list(set(permissions))
    }
