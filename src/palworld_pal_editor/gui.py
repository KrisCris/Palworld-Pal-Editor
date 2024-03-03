import sys
import threading
import time
import webview
from palworld_pal_editor.config import VERSION, Config
from palworld_pal_editor.webui import main as web_main


def main():
    t = threading.Thread(target=web_main)
    t.daemon = True
    t.start()
    time.sleep(3)
    webview.create_window(f"Palworld Pal Editor, developed by _connlost with ❤️. VERSION: {VERSION}", url=f"http://localhost:{Config.port}/", width=1280, height=800, min_size=(960, 600))
    webview.start()
    sys.exit()


if __name__ == "__main__":
    main()
