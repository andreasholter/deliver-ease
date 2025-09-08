from pathlib import Path

from pydantic import BaseModel

from .config import Config
from .exceptionmodel import exception_to_model
from .parsing import parse_json


class RouterConfig(BaseModel):
    disableAuth: bool


class RouterConfigs(BaseModel):
    routers: dict[str, RouterConfig]


def src_path(cfg: Config) -> Path:
    """Path where source is located and PYTHONPATH points to."""
    return Path(cfg.DEVX_APP_ROOT_PATH) / "src"


def read_router_config(cfg: Config) -> RouterConfigs | None:
    """Read router config from file."""
    config_file = src_path(cfg) / "routers.json"
    return (
        parse_json(config_file.read_text(), RouterConfigs)
        if config_file.exists()
        else None
    )


def find_submodules(cfg: Config):
    """Find user defined submodules for dynamic importing."""
    # Parent module we're looking for submodules in
    module_prefix = "app.apis."
    apis_path = src_path(cfg) / "app" / "apis"

    if cfg.DISABLE_API_AS_INIT_PY:
        # New API submodules following **/{name}.py pattern
        submodules = [
            p.relative_to(apis_path).as_posix().removesuffix(".py")
            for p in [p for p in apis_path.glob("**/*.py")]
            if p.name != "__init__.py"
        ]
    else:
        # Old submodules following {name}/__init__.py pattern
        submodules = [
            p.relative_to(apis_path).parent.as_posix()
            for p in apis_path.glob("*/__init__.py")
        ]

    return module_prefix, submodules


def convert_exception_to_model(cfg: Config, ex: BaseException):
    """Make exception model with venv and app paths cleaned up a bit."""

    # Show "/app/src/app/apis/foo/__init__.py as just "app/apis/foo/__init__.py"
    app_path = (src_path(cfg) / "app").as_posix()
    replace_paths = [
        (app_path, "app"),
    ]

    # Present venv path as just "/venv"
    if cfg.VIRTUAL_ENV:
        replace_paths.append((cfg.VIRTUAL_ENV, "/venv"))
    if cfg.RAW_APP_VENV_PATH:
        # This is because we're currently symlinking and the original path shows up in stack traces
        replace_paths.append((cfg.RAW_APP_VENV_PATH, "/venv"))

    return exception_to_model(
        ex,
        root_dir=app_path,
        replace_paths=replace_paths,
    )
