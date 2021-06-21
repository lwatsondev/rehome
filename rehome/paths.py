from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()
CONFIG_DIR = BASE_DIR.parent / "config"
DATA_DIR = BASE_DIR.parent / "data"
STATIC_DIR = BASE_DIR / "static"
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATE_DIR = BASE_DIR / "templates"
RESOURCE_DIR = BASE_DIR / "resources"
