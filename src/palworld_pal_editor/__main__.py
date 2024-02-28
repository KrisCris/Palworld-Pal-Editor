import argparse

from palworld_pal_editor.utils import LOGGER, DataProvider
from palworld_pal_editor.config import Config


def setup_config_from_args():
    parser = argparse.ArgumentParser(description="Your application description here.")
    parser.add_argument('--lang', type=str, help=f'Language for the application, options: {", ".join(DataProvider.get_i18n_options())}..', default='en')
    parser.add_argument('--cli', action='store_true', help='Enable CLI mode.') # TODO remove default=True
    parser.add_argument('--debug', action='store_true', help='Debug option, mimic interactive mode for VSCode debug launch.')
    parser.add_argument('--path', type=str, help='Path to the save folder, the one contains Level.sav', default=None)
    # Unused:
    parser.add_argument('--gui', action='store_true', help='Enable GUI mode.')
    parser.add_argument('--web', action='store_true', help='Enable WebUI.')
    parser.add_argument('--port', type=int, help='Port used for WebUI mode.', default=58080)

    args = parser.parse_args()

    Config.i18n = args.lang
    Config.cli = args.cli
    Config.gui = args.gui
    Config.web = args.web
    Config.port = args.port
    Config.debug = args.debug
    Config.path = args.path

    if not DataProvider.is_valid_i18n(args.lang):
        Config.i18n = DataProvider.default_i18n

def main():
    setup_config_from_args()
    print(f"Language: {Config.i18n}, CLI mode: {Config.cli}")
    if Config.cli:
        from palworld_pal_editor.cli import main as cli_main
        globals().update(cli_main())
    # elif Config.gui:
    #     from palworld_pal_editor.gui import main as gui_main
    #     gui_main()
    else:
        from palworld_pal_editor.webui import main as webui_main
        webui_main()
    # else:
    #     raise NotImplementedError("Unimplemented Mode.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        LOGGER.error(f"Exception caught on __main__: {e}")
