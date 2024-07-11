import json, jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Response, status, Depends
from fastapi.responses import RedirectResponse
from app.config.config import get_settings
from app.models.users import User
from sqlmodel import Session, select
from app.database.session import get_session
from app.schemas.auth import LegacyUserInput
from app.config.exceptions import NotFound

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
            #     private_key = key_file.read()
            # settings['sp']['x509cert'] = certificate
            # settings['sp']['privateKey'] = private_key
        case "production":
            saml_config_file = "app/saml/config/prod_saml_config.json"
            with open(saml_config_file) as f:
                settings = json.load(f)
            # with open("app/saml/production/cert.pem", "r") as cert_file:
            #     certificate = cert_file.read()
            # with open("app/saml/production/key.pem", "r") as key_file:
            #     private_key = key_file.read()
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

def generate_token(user_object, session):
    payload = {
        "user_id": user_object.id,
        "first_name": user_object.first_name,
        "last_name": user_object.last_name,
        "email": user_object.email,
        'exp': datetime.utcnow() + timedelta(minutes=15)  # Token expires in 15 minutes
    }
    token = jwt.encode(payload, "your-secret-key", algorithm="HS256")

    setattr(user_object, "fetch_auth_token", token)

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
        acs_host = forwarded_host
        acs_port = forwarded_port

    return {
        'http_host': acs_host,
        'script_name': request.scope.get('root_path'),
        'server_port': acs_port,
        'https': 'on' if url_data.scheme == 'https' else 'off',
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
        return HTTPException(status_code=500, detail=', '.join(errors))
    return Response(content=metadata, media_type="text/xml")

@router.get("/sso/login")
async def saml_login(request: Request):
    req = await prepare_fastapi_request(request)
    auth = init_saml_auth(req)
    sso_built_url = auth.login()
    return RedirectResponse(sso_built_url)

@router.post("/sso/acs")
async def saml_acs(request: Request, session: Session = Depends(get_session)):
    req = await prepare_fastapi_request(request)
    auth = init_saml_auth(req)
    auth.process_response()
    errors = auth.get_errors()
    last_error_reason = auth.get_last_error_reason()
    if len(errors) > 0 or not auth.is_authenticated():
        # return HTTPException(status_code=400, detail=', '.join(errors))
        # temp debug
        return HTTPException(status_code=400, detail=f"{errors}, last error reason: {last_error_reason}")

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
    user = session.exec(user_query).first()
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

    return RedirectResponse(url=f"{get_settings().VUE_HOST}/?token={token}", status_code=status.HTTP_303_SEE_OTHER)

if get_settings().APP_ENVIRONMENT in ['debug', 'local', 'develop', 'test']:
    # Route only available in non prod envs
    @router.post('/legacy/login')
    async def legacy_login(request: Request, legacy_user: LegacyUserInput, session: Session = Depends(get_session)):
        user_query = select(User).where(User.email==legacy_user.email)
        user = session.exec(user_query).first()
        if not user:
            raise NotFound(detail=f"User not found for {legacy_user.email}")

        token = generate_token(user, session)

        return RedirectResponse(url=f"{get_settings().VUE_HOST}/?token={token}", status_code=status.HTTP_303_SEE_OTHER)
