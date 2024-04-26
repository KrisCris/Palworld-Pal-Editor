from palworld_pal_editor.config import PROGRAM_PATH
from palworld_pal_editor.utils.logger import Logger, ColorConsoleFormatter

LOGGER = Logger(log_directory=PROGRAM_PATH / "logs")

from palworld_pal_editor.utils.util import *
from palworld_pal_editor.utils.data_provider import DataProvider