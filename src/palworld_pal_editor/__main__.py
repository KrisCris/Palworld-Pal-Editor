import argparse
import traceback

from palworld_pal_editor.utils import LOGGER, DataProvider, check_or_generate_port
from palworld_pal_editor.config import PROGRAM_PATH, Config, version_info, is_gh_build, CONFIG_PATH

from palworld_pal_editor.cli import InteractThread, main as cli_main
from palworld_pal_editor.gui import main as gui_main
from palworld_pal_editor.webui import main as webui_main


def setup_config_from_args():
    try: 
        Config.load_from_file()
    except:
        LOGGER.warning(f"Failed Loading Config from {CONFIG_PATH}: {traceback.format_exc()}")

    parser = argparse.ArgumentParser(description="Palworld Pal Editor, developed by _connlost with ❤.")

    parser.add_argument('--lang', type=str, help=f'Language for the application. options: {", ".join(DataProvider.get_i18n_options())}', default=Config.i18n)
    parser.add_argument('--path', type=str, help='Path to the save folder.', default=Config.path)
    parser.add_argument('--mode', type=str, help='Running Mode, options: cli, gui, web', default=Config.mode)
    parser.add_argument('--port', type=int, help='Port used for WebUI mode.', default=Config.port)
    parser.add_argument('--password', type=str, help='Password for WebUI.', default=Config.password)
    
    parser.add_argument('--debug', action='store_true', help='The debug option, only for VSCode debug launch. (Never saved to config.json)')
    parser.add_argument('--nocli', action='store_true', help='Disable Interactive CLI on GUI/WEB mode. (Never saved to config.json)')

    args = parser.parse_args()
    try:
        Config.set_configs({
            "debug": args.debug, # never saved to config.json
            "nocli": args.nocli, # never saved to config.json
            "path": args.path,
            "mode": args.mode,
            "port": args.port,
            "password": args.password,
            "i18n": args.lang
        })

        if not DataProvider.is_valid_i18n(Config.i18n):
            LOGGER.warning(f"Invalid --i18n {Config.i18n}, default to en.")
            Config.set_config("i18n", DataProvider.default_i18n)

        modes = ["cli", "gui", "web"]
        if Config.mode not in modes:
            Config.set_config("mode", "gui")
            LOGGER.warning(f"Invalid --mode {Config.mode}, default to GUI.")

        if not Config.debug:
            if (port := check_or_generate_port(Config.port)) != Config.port:
                LOGGER.warning(f"Port {Config.port} not available, use {port} instead.")
                Config.set_config("port", port)

        LOGGER.info(f"Config file written to {PROGRAM_PATH / 'config.json'}")
    except:
        LOGGER.warning(f"Failed Saving Config {str(Config.__str__())} to {CONFIG_PATH}: {traceback.format_exc()}")

def main():
    setup_config_from_args()
    LOGGER.info(Config.__str__())
    VER = version_info()
    LOGGER.info(f"Running Palworld-Pal-Editor version: {VER}")
    if not is_gh_build():
        LOGGER.warning("This version is not built by the official CI/CD pipeline. Be cautious and verify the source.")
    match Config.mode:
        case "cli": cli_main()
        case "gui": 
            if not Config.nocli: InteractThread.load()
            gui_main()
        case "web": 
            if not Config.nocli: InteractThread.load()
            webui_main()

if __name__ == "__main__":
    LOGGER.info(f"Logs written to {PROGRAM_PATH / 'logs'}")
    
    try:
        main()
    except Exception as e:
        LOGGER.error(f"Exception caught on __main__: {traceback.format_exc()}")
