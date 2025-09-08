import functools
import os
from enum import Enum
from typing import Any

from pydantic import BaseModel

from .extensions.firebase_auth import (
    FirebaseExtensionConfig,
    get_firebase_audience,
    get_firebase_issuer,
)
from .extensions.stack_auth import (
    StackAuthExtensionConfig,
    get_stack_auth_audience,
    get_stack_auth_issuer,
)
from .parsing import parse_json_list
from .utils import debug_enabled


class ExtensionType(str, Enum):
    """Type of extension."""

    shadcn = "shadcn"
    firebase_auth = "firebase-auth"
    stack_auth = "stack-auth"
    neon_database = "neon-database"
    mcp = "mcp"


class Extension(BaseModel):
    # Note: Fallback to str for less strict parsing across versions etc
    name: ExtensionType | str
    version: str
    config: dict[str, Any] | None = None


class Config(BaseModel):
    ENVIRONMENT: str = "development"

    DATABUTTON_PROJECT_ID: str = ""
    DATABUTTON_SERVICE_TYPE: str = ""

    DATABUTTON_EXTENSIONS: str = ""

    # Port of the internal devx server
    DEVX_API_PORT: int | None = None
    DEVX_URL_INTERNAL: str | None = None

    # Toggle publishing messages to devx server
    ENABLE_WORKSPACE_PUBLISH: bool | None = None

    # Root path of the app
    # TODO: Rearrange the backend paths and make this point to the backend part not the app root
    DEVX_APP_ROOT_PATH: str = ""
    VIRTUAL_ENV: str = ""
    RAW_APP_VENV_PATH: str = ""

    # The external host we're served from
    DEVX_HOST: str = ""

    # The external url path that devx_url_internal is exposed as
    DEVX_BASE_PATH: str = ""

    # TODO: Only used for this, replace both with a single SERVER_URL
    # servers=[{"url": f"{cfg.DEVX_HOST}{cfg.DEVX_BASE_PATH}/app"}],

    USER_API_PORT: int = 9999

    ENABLE_MCP: bool = False
    INTERNAL_MCP_TOKEN: str = ""

    DISABLE_API_AS_INIT_PY: bool = False


@functools.cache
def parse_extensions(databutton_extensions: str) -> list[Extension]:
    extensions: list[Extension] = []
    if not databutton_extensions:
        print("No extensions env var")
    else:
        extensions = parse_json_list(databutton_extensions, Extension)
        if len(extensions) == 0:
            print("No extensions found")
        else:
            print(f"Found extensions: {[e.name for e in extensions]}")
    return extensions


def get_extensions(cfg: Config) -> list[Extension]:
    return parse_extensions(cfg.DATABUTTON_EXTENSIONS)


def get_extension(cfg: Config, name: ExtensionType) -> Extension | None:
    extensions = [e for e in get_extensions(cfg) if e.name == name]
    if not extensions:
        return None
    if len(extensions) > 1:
        print(f"WARNING: Got duplicate extension: {extensions}")
    return extensions[0]


class AuthConfig(BaseModel):
    issuer: str
    jwks_url: str
    audience: str


def get_firebase_extension_config(cfg: Config) -> FirebaseExtensionConfig | None:
    extension = get_extension(cfg, ExtensionType.firebase_auth)
    if not extension:
        return None
    if not extension.config:
        raise ValueError("Expecting extension config")
    return FirebaseExtensionConfig(**extension.config)


def get_stack_auth_extension_config(cfg: Config) -> StackAuthExtensionConfig | None:
    extension = get_extension(cfg, ExtensionType.stack_auth)
    if not extension:
        return None
    if not extension.config:
        raise ValueError("Expecting extension config")
    return StackAuthExtensionConfig(**extension.config)


def parse_auth_configs(cfg: Config) -> list[AuthConfig]:
    # Each auth config has an audience and a jwks url to get signing key from,
    # the jwt bearer token is validated with the signing key from jwks urls
    # matching the audience found in the token
    auth_configs: list[AuthConfig] = []

    # Add firebase auth config if extension is enabled
    firebase_extension = get_extension(cfg, ExtensionType.firebase_auth)
    if firebase_extension and firebase_extension.config:
        fbcfg = FirebaseExtensionConfig(**firebase_extension.config)
        auth_configs.append(
            AuthConfig(
                issuer=get_firebase_issuer(fbcfg),
                jwks_url="https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com",
                audience=get_firebase_audience(fbcfg),
            )
        )

    # Add stack auth config if extension is enabled
    stack_auth_extension = get_extension(cfg, ExtensionType.stack_auth)
    if stack_auth_extension and stack_auth_extension.config:
        stackcfg = StackAuthExtensionConfig(**stack_auth_extension.config)
        auth_configs.append(
            AuthConfig(
                issuer=get_stack_auth_issuer(stackcfg),
                jwks_url=stackcfg.jwksUrl,
                audience=get_stack_auth_audience(stackcfg),
            )
        )

    # TODO: Add other JWKS compatible auth integrations like supabase here

    # The rest of the auth configs will be added only if the above configs are present
    if len(auth_configs) == 0:
        return auth_configs

    # TODO: This is only used in the mcp server for now, want to add api tokens for endpoints later
    # Config for databutton signed api tokens with the app as audience
    # auth_configs.append(
    #     AuthConfig(
    #         issuer="https://securetoken.google.com/databutton",
    #         jwks_url="https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com",
    #         audience="databutton",
    #         require_dbtn_claims={
    #             "appId": cfg.DATABUTTON_PROJECT_ID,
    #             "env": cfg.DATABUTTON_SERVICE_TYPE,
    #         },
    #     )
    # )

    # Add internal devx audience and jwks url to get signing key from for test tokens
    if cfg.DATABUTTON_SERVICE_TYPE == "devx":
        auth_configs.append(
            AuthConfig(
                issuer=f"https://api.databutton.com/_projects/{cfg.DATABUTTON_PROJECT_ID}/dbtn/devx/workspace/auth",
                jwks_url=f"{cfg.DEVX_URL_INTERNAL}/workspace/auth/jwks",
                audience=f"https://api.databutton.com/_projects/{cfg.DATABUTTON_PROJECT_ID}/dbtn/devx",
            )
        )

    return auth_configs


def log_config(
    cfg: Config,
):
    lines = [
        "Environment",
        f"path = {os.environ.get('PATH')}",
        f"pythonpath = {os.environ.get('PYTHONPATH')}",
        f"virtual_env = {os.environ.get('VIRTUAL_ENV')}",
        "Config",
        f"environment               = {cfg.ENVIRONMENT}",
        f"project_id                = {cfg.DATABUTTON_PROJECT_ID}",
        f"service_type              = {cfg.DATABUTTON_SERVICE_TYPE}",
        f"app_path                  = {cfg.DEVX_APP_ROOT_PATH}",
        f"devx_api_port             = {cfg.DEVX_API_PORT}",
        f"devx_url_internal         = {cfg.DEVX_URL_INTERNAL}",
        f"enable_workspace_publish  = {cfg.ENABLE_WORKSPACE_PUBLISH}",
        f"devx_host                 = {cfg.DEVX_HOST}",
        f"devx_base_path            = {cfg.DEVX_BASE_PATH}",
        f"databutton_extensions     = {cfg.DATABUTTON_EXTENSIONS}",
    ]
    print("\n".join(lines))


def validate_config(cfg: Config):
    issues: list[str] = []
    if not cfg.DATABUTTON_PROJECT_ID:
        issues.append("Missing DATABUTTON_PROJECT_ID")
    if not cfg.DATABUTTON_SERVICE_TYPE:
        issues.append("Missing DATABUTTON_SERVICE_TYPE")
    if not cfg.DEVX_API_PORT:
        issues.append("Missing DEVX_API_PORT")
    if not cfg.DEVX_URL_INTERNAL:
        issues.append("Missing DEVX_URL_INTERNAL")
    if not cfg.DEVX_APP_ROOT_PATH:
        issues.append("Missing app root path.")

    try:
        parse_extensions(cfg.DATABUTTON_EXTENSIONS)
    except Exception as e:
        issues.append(f"Failed to parse extensions: {e}")

    if issues:
        if cfg.ENVIRONMENT == "development":
            for msg in issues:
                print("WARNING:", msg)
        else:
            raise ValueError("\n".join(issues))


def parse_environment() -> Config:
    """Read config from env vars.

    Instead of using BaseSettings, just read env vars directly,
    avoiding the dependency on pydantic_settings.
    """
    cfg = Config()
    for k in cfg.__dict__.keys():
        if k in os.environ:
            setattr(cfg, k, os.environ[k])
    return cfg


def checked_config(cfg: Config | None = None) -> Config:
    """Read config from environment if not passed in, and validate it before returning."""
    if cfg is None:
        cfg = parse_environment()

    # TODO: Set this outside app?
    if cfg.ENABLE_WORKSPACE_PUBLISH is None:
        cfg.ENABLE_WORKSPACE_PUBLISH = cfg.DATABUTTON_SERVICE_TYPE != "prodx"

    # TODO: Set this outside app?
    if cfg.DEVX_API_PORT and not cfg.DEVX_URL_INTERNAL:
        cfg.DEVX_URL_INTERNAL = f"http://localhost:{cfg.DEVX_API_PORT}"

    if debug_enabled():
        log_config(cfg)

    validate_config(cfg)

    return cfg
