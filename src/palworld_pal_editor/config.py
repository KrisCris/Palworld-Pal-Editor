import json
from pathlib import Path
import sys

PROGRAM_PATH = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.resolve()
if hasattr(sys, 'frozen'):
    if hasattr(sys, "_MEIPASS"):
        ASSETS_PATH = Path(sys._MEIPASS)
    else:
        ASSETS_PATH = Path(sys.executable).parent
else:
    ASSETS_PATH = Path(__file__).parent

VERSION = "0.4.1"

class Config:
    i18n: str = "en"
    mode: str = "gui"
    port: int = 58080
    debug: bool = False
    path: str = None
    password: str = None
    _password_hash: str = None
    JWT_SECRET_KEY: str = "X2Nvbm5sb3N0"

    @classmethod
    def load_from_file(cls, file_path: str):
        """Load configuration values from a JSON file using pathlib."""
        path = Path(file_path)
        if path.exists():
            with path.open("r") as file:
                data = json.load(file)
                for key, value in data.items():
                    if hasattr(cls, key):
                        setattr(cls, key, value)

    @classmethod
    def save_to_file(cls, file_path: str):
        """Save current configuration values to a JSON file using the to_dict method and pathlib."""
        config_data = cls.to_dict()
        path = Path(file_path)
        with path.open("w") as file:
            json.dump(config_data, file, indent=4)

    @classmethod
    def __str__(cls):
        dic = cls.to_dict()
        attrs = [f"{key}: {dic[key]}" for key in dic]
        return ", ".join(attrs)

    @classmethod
    def to_dict(cls):
        return {
            'i18n': Config.i18n,
            'mode': Config.mode,
            'port': Config.port,
            'path': Config.path,
            'password': Config.password,
            'JWT_SECRET_KEY': Config.JWT_SECRET_KEY
        }
