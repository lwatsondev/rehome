from logging.config import dictConfig
from pathlib import Path

import yaml
from flask import Flask

BASE_DIR = Path(__file__).parent.absolute()
CONFIG_DIR = BASE_DIR.parent / "config"
DATA_DIR = BASE_DIR.parent / "data"
STATIC_DIR = BASE_DIR / "static"
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATE_DIR = BASE_DIR / "templates"


def create_app():
    create_data_directories()
    setup_logging()
    app = Flask(
        "rehome", static_folder=str(STATIC_DIR), template_folder=str(TEMPLATE_DIR)
    )

    register_blueprints(app)
    return app


def register_blueprints(app):
    from rehome import views

    views.register_blueprints(app)
    app.logger.debug("Blueprints registered.")


def create_data_directories():
    for directory in [CONFIG_DIR, DATA_DIR]:
        directory.mkdir(exist_ok=True)


def setup_logging(file: Path = CONFIG_DIR / "logging.yml"):
    try:
        dictConfig(yaml.safe_load(file.read_text()))
    except (FileNotFoundError, TypeError):
        setup_logging(ASSETS_DIR / "config" / "logging.yml")
