import argparse

from palworld_pal_editor.utils import LOGGER
from palworld_pal_editor.config import Config
from palworld_pal_editor.data_provider import I18N_LIST


def setup_config_from_args():
    parser = argparse.ArgumentParser(description="Your application description here.")
    parser.add_argument('--lang', type=str, help=f'Language for the application, options: {", ".join(I18N_LIST)}..', default='en')
    # TODO remove default=True
    parser.add_argument('--cli', action='store_true', help='Enable CLI mode.', default=True)
    parser.add_argument('--debug', action='store_true', help='Debug option, mimic interactive mode for VSCode debug launch.')

    args = parser.parse_args()

    Config.i18n = args.lang
    Config.cli = args.cli
    Config.debug = args.debug

    if args.lang not in I18N_LIST:
        Config.i18n = I18N_LIST[0]

def main():
    setup_config_from_args()
    print(f"Language: {Config.i18n}, CLI mode: {Config.cli}")
    if Config.cli:
        from palworld_pal_editor.cli import main as cli_main
        globals().update(cli_main())
    else:
        raise NotImplementedError("NO GUI Mode Yet, run with --cli.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        LOGGER.error(f"Exception caught on __main__: {e}")
