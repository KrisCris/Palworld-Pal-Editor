import os
import sys
import threading
import time
import traceback
import webbrowser

import requests
import webview

from palworld_pal_editor.config import Config, version_info
from palworld_pal_editor.utils import LOGGER
from palworld_pal_editor.webui import main as web_main


def is_current_backend(response):
    try:
        return (
            response.status_code == 200
            and response.json()["data"]["pid"] == os.getpid()
        )
    except (KeyError, TypeError, ValueError):
        return False


def main():
    port = Config.get_runtime_port()
    t = threading.Thread(target=web_main)
    t.daemon = True
    t.start()
    
    while True:
        LOGGER.info("Waiting for backend response...")
        try:
            response = requests.get(
                f"http://127.0.0.1:{port}/api/ready", timeout=2
            )
            if is_current_backend(response):
                LOGGER.info("Backend ready, launching GUI...")
                break
            LOGGER.error(
                f"Port {port} is responding from another process. "
                "Close it and restart this program."
            )
            return
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if not t.is_alive():
                LOGGER.error("Backend failed to start. Check the log for details.")
                return
            time.sleep(0.5)

    LOGGER.info("If GUI doesn't work for you, check out this post: https://github.com/KrisCris/Palworld-Pal-Editor/issues/4")

    try:
        webview.create_window(f"Palworld Pal Editor, developed by _connlost with ❤️. VERSION: {version_info()}", url=f"http://127.0.0.1:{port}/", width=1600, height=1000, min_size=(960, 600))
        webview.start(private_mode=False)
    except KeyboardInterrupt:
        pass
    except:
        LOGGER.warning(f"Failed Launching pywebview: {traceback.format_exc()}")
        LOGGER.info(f"Fallback to web browser, opening http://127.0.0.1:{port} ...")
        threading.Timer(1, lambda: webbrowser.open(f"http://127.0.0.1:{port}") ).start()
        t.join()
    sys.exit()

if __name__ == "__main__":
    main()
