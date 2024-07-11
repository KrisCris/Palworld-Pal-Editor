import sys
import threading
import time
import requests
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from palworld_pal_editor.config import VERSION, Config
from palworld_pal_editor.utils import LOGGER
from palworld_pal_editor.webui import main as web_main

class MainWindow(QWebEngineView):
    def __init__(self, url):
        super().__init__()
        self.setWindowTitle(f"Palworld Pal Editor, developed by _connlost with ❤️. VERSION: {VERSION}")
        self.setMinimumSize(1280, 720)
        self.load(url)
        self.resize(1600, 900)

def main():
    t = threading.Thread(target=web_main)
    t.daemon = True
    t.start()

    while True:
        LOGGER.info("Waiting for backend response...")
        try:
            response = requests.get(f"http://127.0.0.1:{Config.port}/api/ready")
            if response.status_code == 200:
                LOGGER.info("Backend Ready, Launching GUI...")
                break
            time.sleep(0.5)
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)

    app = QApplication(sys.argv)
    window = MainWindow(f"http://127.0.0.1:{Config.port}/")
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
