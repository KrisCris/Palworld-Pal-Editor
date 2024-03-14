from functools import wraps
import logging
from datetime import datetime
import copy
from pathlib import Path
from typing import Callable
from flask import request

class ColorConsoleFormatter(logging.Formatter):
    """Custom formatter for adding colors to console output only."""
    color_codes = {
        logging.DEBUG: "\033[38;20m",  # Grey
        logging.INFO: "\033[32;20m",   # Green
        logging.WARNING: "\033[33;20m",  # Yellow
        logging.ERROR: "\033[31;20m",  # Red
        logging.CRITICAL: "\033[31;1m",  # Bold Red
    }
    reset_code = "\033[0m"

    def format(self, record):
        log_fmt = f"%(asctime)s %(levelname)s %(message)s"
        datefmt = '%Y-%m-%d %H:%M:%S'
        
        levelname_color = self.color_codes.get(record.levelno, self.reset_code)
        record.levelname = f"{levelname_color}[{record.levelname}]{self.reset_code}"
        
        formatter = logging.Formatter(log_fmt, datefmt)
        return formatter.format(record)

class Logger:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, name="Palworld-Pal-Editor", log_directory="logs", level=logging.DEBUG):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.log_directory = Path(log_directory)
            self.log_directory.mkdir(parents=True, exist_ok=True)

            log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")
            log_path = self.log_directory / log_filename

            self.logger = logging.getLogger(name)
            self.logger.setLevel(level)
            self.logger.propagate = False

            file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

            console_formatter = ColorConsoleFormatter()
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

    def newline(self):
        print("")

    def _print_change(self, entity, val_name, old_val, new_val):
        self.info(f"{entity} | {val_name}: {old_val} -> {new_val}")

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def change_logger(self, attr_name: str):
        """A decorator for logging changes to a property, applicable to any class instance method."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(instance, *args, **kwargs):
                # Retrieve the old value of the attribute
                # copy for ref'd objects
                old_value = getattr(instance, attr_name)
                if isinstance(old_value, (list, dict)):
                    old_value = copy.copy(old_value)
                # Call the original function (setter) with the new value
                og_retval = func(instance, *args, **kwargs)
                # Retrieve the updated value of the attribute
                updated_value = getattr(instance, attr_name)
                # Log the change using a logging mechanism (LOGGER needs to be defined)
                self._print_change(instance, attr_name, old_value, updated_value)
                return og_retval
            return wrapper
        return decorator

    def api_logger(self, func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            self.info(f"API Path: {request.path}")
            self.info(f"Request Body: {request.get_json()}")
            response = func(*args, **kwargs)
            self.info(f"Response: {response}")

            return response
        return decorated_function
