import argparse
import traceback

from palworld_pal_editor.utils import LOGGER, DataProvider
from palworld_pal_editor.config import PROGRAM_PATH, Config, VERSION

from palworld_pal_editor.cli import main as cli_main
from palworld_pal_editor.gui import main as gui_main
from palworld_pal_editor.webui import main as webui_main


def setup_config_from_args():
    CONFIG_PATH = PROGRAM_PATH / 'config.json'
    try: 
        Config.load_from_file(CONFIG_PATH)
    except:
        LOGGER.warning(f"Failed Loading Config from {CONFIG_PATH}: {traceback.format_exc()}")

    parser = argparse.ArgumentParser(description="Palworld Pal Editor, developed by _connlost with ❤.")

    parser.add_argument('--lang', type=str, help=f'Language for the application. options: {", ".join(DataProvider.get_i18n_options())}', default=Config.i18n)
    parser.add_argument('--debug', action='store_true', help='Debug option, only mimics interactive mode for VSCode debug launch.', default=Config.debug)
    parser.add_argument('--path', type=str, help='Path to the save folder.', default=Config.path)
    parser.add_argument('--mode', type=str, help='Running Mode, options: cli, gui, web', default=Config.mode)
    parser.add_argument('--port', type=int, help='Port used for WebUI mode.', default=Config.port)
    parser.add_argument('--password', type=str, help='Password for WebUI.', default=Config.password)

    args = parser.parse_args()

    Config.debug = args.debug
    Config.path = args.path
    Config.mode = args.mode
    Config.port = args.port
    Config.password = args.password
    Config.i18n = args.lang

    if not DataProvider.is_valid_i18n(Config.i18n):
        Config.i18n = DataProvider.default_i18n

    modes = ["cli", "gui", "web"]
    if Config.mode not in modes:
        Config.mode = "gui"
        LOGGER.warning(f"Invalid --mode {Config.mode}, default to GUI.")

    try:
        Config.save_to_file(PROGRAM_PATH / 'config.json')
        LOGGER.info(f"Config file written to {PROGRAM_PATH / 'config.json'}")
    except:
        LOGGER.warning(f"Failed Saving Config {str(Config.__str__())} to {CONFIG_PATH}: {traceback.format_exc()}")


def main():
    setup_config_from_args()
    LOGGER.info(Config.__str__())
    LOGGER.info(f"Running Palworld-Pal-Editor version: {VERSION}")
    match Config.mode:
        # case "cli": globals().update(cli_main())
        case "cli": cli_main()
        case "gui": gui_main()
        case "web": webui_main()

if __name__ == "__main__":
    LOGGER.info(f"Logs written to {PROGRAM_PATH / 'logs'}")
    
    try:
        main()
    except Exception as e:
        LOGGER.error(f"Exception caught on __main__: {traceback.format_exc()}")
