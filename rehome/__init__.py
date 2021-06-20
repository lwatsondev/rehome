from pathlib import Path

from flask import Flask

BASE_DIR = Path(__file__).parent.absolute()
CONFIG_DIR = BASE_DIR.parent / "config"
DATA_DIR = BASE_DIR.parent / "data"
STATIC_DIR = BASE_DIR / "static"
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATE_DIR = BASE_DIR / "templates"


def create_app():
    app = Flask(
        "rehome", static_folder=str(STATIC_DIR), template_folder=str(TEMPLATE_DIR)
    )
    return app
