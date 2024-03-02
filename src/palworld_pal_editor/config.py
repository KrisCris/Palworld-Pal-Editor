import json
import os


class Config:
    i18n: str = "en"
    mode: str = "gui"
    # cli: bool = False
    # gui: bool = False
    # web: bool = False
    port: int = 58080
    debug: bool = False
    path: str = None
    password: str = None
    password_hash: str = None
    JWT_SECRET_KEY: str = "X2Nvbm5sb3N0"

    @classmethod
    def load_from_file(cls, file_path: str):
        """Load configuration values from a JSON file."""
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                data = json.load(file)
                for key, value in data.items():
                    if hasattr(cls, key):
                        setattr(cls, key, value)

    @classmethod
    def save_to_file(cls, file_path: str):
        """Save current configuration values to a JSON file using the to_dict method."""
        config_data = cls.to_dict()
        with open(file_path, 'w') as file:
            json.dump(config_data, file, indent=4)

    @classmethod
    def __str__(cls):
        attrs = []
        for attr, value in cls.__dict__.items():
            if not attr.startswith('__') and not callable(value) and not isinstance(value, classmethod):
                attrs.append(f"{attr}: {value}")
        return ", ".join(attrs)
    
    @classmethod
    def to_dict(cls):
        attrs = {}
        for attr, value in cls.__dict__.items():
            if not attr.startswith('__') and not callable(value) and not isinstance(value, classmethod):
                attrs[attr] = value
        return attrs
