import shutil
import sys
from pathlib import Path
from typing import Union

import yaml
from dotty_dict import Dotty, dotty
from yaml import YAMLError

from paths import CONFIG_DIR, RESOURCE_DIR


class ConfigFile(object):
    def __init__(self, filename: Union[Path, str] = "config.yml"):
        super().__init__()
        self._default_file_path = RESOURCE_DIR / "config" / filename
        self._file_path = CONFIG_DIR / filename
        self._container = dotty()

    def save_default(self):
        if not self._default_file_path.exists() or self._file_path.exists():
            return

        mkdir_args = {"parents": True, "exist_ok": True}
        if self._file_path.is_dir():
            self._file_path.mkdir(**mkdir_args)
        else:
            self._file_path.parent.mkdir(**mkdir_args)

        default_relative_path = self._default_file_path.relative_to(Path.cwd())
        relative_path = self._file_path.relative_to(Path.cwd())
        shutil.copy2(self._default_file_path, self._file_path)
        print(f"Copied {default_relative_path} to {relative_path}")

    def load(self, exit_on_error=False) -> Dotty:
        for file in [self._default_file_path, self._file_path]:
            try:
                self._container.update(yaml.safe_load(file.read_text()))
            except (TypeError, FileNotFoundError):
                pass
            except YAMLError as exc:
                print(f"Error loading {self._file_path.relative_to(Path.cwd())}: {exc}")
                if exit_on_error:
                    sys.exit(1)

        return self._container


class Config(object):
    SOCIAL_LINKS: dict[str, str]

    def __init__(self):
        config_file = ConfigFile()
        config_file.save_default()
        config_dict = config_file.load(exit_on_error=True)

        self.SOCIAL_LINKS = config_dict.get("social_links")
