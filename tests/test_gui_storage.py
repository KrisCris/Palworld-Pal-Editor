import unittest
from unittest.mock import Mock, patch

from palworld_pal_editor import gui


class GuiStorageTests(unittest.TestCase):
    def test_gui_starts_webview_with_persistent_browser_storage(self):
        backend_thread = Mock()
        with (
            patch.object(gui.threading, "Thread", return_value=backend_thread),
            patch.object(gui.requests, "get", return_value=Mock(status_code=200)),
            patch.object(gui.webview, "create_window"),
            patch.object(gui.webview, "start") as start,
            patch.object(gui.sys, "exit"),
            patch.object(gui, "LOGGER"),
        ):
            gui.main()

        start.assert_called_once_with(private_mode=False)


if __name__ == "__main__":
    unittest.main()
