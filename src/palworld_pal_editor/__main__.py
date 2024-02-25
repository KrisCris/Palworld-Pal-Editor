import code
import sys
import argparse

from palworld_pal_editor.save_manager import SaveManager
from palworld_pal_editor.utils import Logger
from palworld_pal_editor.config import Config
from palworld_pal_editor.data_provider import I18N_LIST

LOGGER = Logger()

def setup_config_from_args():
    parser = argparse.ArgumentParser(description="Your application description here.")
    parser.add_argument('--language', type=str, help=f'Language for the application, options: {", ".join(I18N_LIST)}..', default='en')
    parser.add_argument('--cli', action='store_true', help='Enable CLI mode.')

    args = parser.parse_args()

    Config.i18n = args.language
    Config.cli = args.cli

    if args.language not in I18N_LIST:
        Config.i18n = I18N_LIST[0]

def main():
    setup_config_from_args()
    print(f"Language: {Config.i18n}, CLI mode: {Config.cli}")
    if Config.cli:
        from palworld_pal_editor.cli import main as cli_main
        cli_main()
    else:
        raise NotImplementedError("NO GUI Mode Yet, run with --cli.")

if __name__ == "__main__":
    main()
