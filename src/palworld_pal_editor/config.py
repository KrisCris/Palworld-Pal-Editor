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

CONFIG_PATH = PROGRAM_PATH / 'config.json'

VERSION = "0.0.0"
RELEASE_TYPE = "NIGHTLY"
BUILD_TIME = "0000000001"
GIT_HASH = "0000000"
REPO = "undefined"

def version_info() -> str:
    if GIT_HASH == "0000000":
        return "development"
    if RELEASE_TYPE == "NIGHTLY":
        return f"{VERSION}-{RELEASE_TYPE}-{GIT_HASH}-{REPO}-{BUILD_TIME}"
    if RELEASE_TYPE == "RELEASE":
        return f"{VERSION}-{RELEASE_TYPE}-{GIT_HASH}"

def is_gh_build() -> bool:
    return GIT_HASH != "0000000"

class Config:
    i18n: str = "en"
    mode: str = "gui"
    port: int = 58080
    debug: bool = False
    path: str = None
    password: str = None
    nocli: bool = False
    _password_hash: str = None
    JWT_SECRET_KEY: str = "X2Nvbm5sb3N0"
    shownDonateInfo: dict[str, bool] = {}

    @classmethod
    def load_from_file(cls, file_path: str=CONFIG_PATH):
        """Load configuration values from a JSON file using pathlib."""
        path = Path(file_path)
        if path.exists():
            with path.open("r") as file:
                data = json.load(file)
                for key, value in data.items():
                    if hasattr(cls, key):
                        setattr(cls, key, value)

    @classmethod
    def set_configs(cls, attrs: dict):
        for key, value in attrs.items():
            if hasattr(cls, key):
                setattr(cls, key, value)
        Config.save_to_file()

    @classmethod
    def set_config(cls, key, value):
        if hasattr(cls, key):
            setattr(cls, key, value)
        Config.save_to_file()

    @classmethod
    def set_shown_donate_info(cls):
        cls.shownDonateInfo[Config.i18n] = True
        Config.save_to_file()

    @classmethod
    def save_to_file(cls, file_path: str=CONFIG_PATH):
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
            'JWT_SECRET_KEY': Config.JWT_SECRET_KEY,
            'shownDonateInfo': Config.shownDonateInfo
        }
