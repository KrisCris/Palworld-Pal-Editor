import sys
import threading
import time
import traceback
import webbrowser
import webview
from palworld_pal_editor.config import VERSION, Config
from palworld_pal_editor.utils import LOGGER
from palworld_pal_editor.webui import main as web_main


def main():
    t = threading.Thread(target=web_main)
    t.daemon = True
    t.start()
    try:
        webview.create_window(f"Palworld Pal Editor, developed by _connlost with ❤️. VERSION: {VERSION}", url=f"http://localhost:{Config.port}/", width=1600, height=1000, min_size=(960, 600))
        webview.start()
    except:
        LOGGER.warning(f"Failed Launching pywebview: {traceback.format_exc()}")
        LOGGER.info("Fallback to web browser...")
        threading.Timer(1, lambda: webbrowser.open(f"http://127.0.0.1:{Config.port}") ).start()
        t.join()
    sys.exit()

if __name__ == "__main__":
    main()
