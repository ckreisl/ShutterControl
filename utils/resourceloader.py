from __future__ import annotations

import json

from configparser import ConfigParser
from pathlib import Path


LOCATION: Path = Path(__file__).parent.parent / 'resources'


class ResourceLoader:
    
    @staticmethod
    def load_json(filename: str) -> dict:
        with open(LOCATION / filename, encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def load_ini(filename: str) -> ConfigParser:
        config = ConfigParser()
        config.read(LOCATION / filename)
        return config

    @staticmethod
    def load_config() -> ConfigParser:
        return ResourceLoader.load_ini('.shutterControl.ini')
