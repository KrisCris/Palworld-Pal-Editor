import logging
import os
from datetime import datetime

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

    def __init__(self, name="PalEditor", log_directory="logs", level=logging.DEBUG):
        if not hasattr(self, 'initialized'):  # This check prevents reinitialization
            self.initialized = True
            self.log_directory = log_directory
            os.makedirs(self.log_directory, exist_ok=True)
            log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")
            log_path = os.path.join(self.log_directory, log_filename)

            self.logger = logging.getLogger(name)
            self.logger.setLevel(level)

            file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(level)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

            console_formatter = ColorConsoleFormatter()
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

if __name__ == "__main__":
    logger = Logger()
    logger.debug('This is a debug message')
    logger.info('This is an info message')
    logger.warning('This is a warning message')
    logger.error('This is an error message')
    logger = Logger()
    logger.debug('This is a debug message')
    logger.info('This is an info message')
    logger.warning('This is a warning message')
    logger.error('This is an error message')    
    logger = Logger()
    logger.debug('This is a debug message')
    logger.info('This is an info message')
    logger.warning('This is a warning message')
    logger.error('This is an error message')    
    logger = Logger()
    logger.debug('This is a debug message')
    logger.info('This is an info message')
    logger.warning('This is a warning message')
    logger.error('This is an error message')    
    logger = Logger()
    logger.debug('This is a debug message')
    logger.info('This is an info message')
    logger.warning('This is a warning message')
    logger.error('This is an error message')