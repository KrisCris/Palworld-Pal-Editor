from .save_manager import SaveManager
from .utils import Logger

LOGGER = Logger()

if __name__ == "__main__":
    LOGGER.info("> Please provide the path to Level.sav")
    input_path = input()
    sm = SaveManager()
    sm.open(input_path)
    pass
