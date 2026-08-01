import os
import unittest
from unittest.mock import Mock, patch

from palworld_pal_editor import gui


class GuiStorageTests(unittest.TestCase):
    def test_gui_starts_webview_with_persistent_browser_storage(self):
        backend_thread = Mock()
        request = Mock(
            return_value=Mock(
                status_code=200,
                json=Mock(return_value={"data": {"pid": os.getpid()}}),
            )
        )
        with (
            patch.object(gui.threading, "Thread", return_value=backend_thread),
            patch.object(gui.Config, "_runtime_port", 63886),
            patch.object(gui.requests, "get", request),
            patch.object(gui.webview, "create_window") as create_window,
            patch.object(gui.webview, "start") as start,
            patch.object(gui.sys, "exit"),
            patch.object(gui, "LOGGER"),
        ):
            gui.main()

        request.assert_called_once_with("http://127.0.0.1:63886/api/ready", timeout=2)
        self.assertEqual(create_window.call_args.kwargs["url"], "http://127.0.0.1:63886/")
        start.assert_called_once_with(private_mode=False)

    def test_gui_rejects_a_port_owned_by_another_service(self):
        backend_thread = Mock()
        request = Mock(return_value=Mock(status_code=404))
        with (
            patch.object(gui.threading, "Thread", return_value=backend_thread),
            patch.object(gui.requests, "get", request),
            patch.object(gui.time, "sleep", side_effect=AssertionError("retried")),
            patch.object(gui.webview, "create_window") as create_window,
            patch.object(gui.webview, "start") as start,
            patch.object(gui, "LOGGER"),
        ):
            gui.main()

        request.assert_called_once_with(
            f"http://127.0.0.1:{gui.Config.port}/api/ready", timeout=2
        )
        create_window.assert_not_called()
        start.assert_not_called()

    def test_gui_stops_waiting_when_its_backend_thread_exits(self):
        backend_thread = Mock()
        backend_thread.is_alive.return_value = False
        with (
            patch.object(gui.threading, "Thread", return_value=backend_thread),
            patch.object(
                gui.requests,
                "get",
                side_effect=gui.requests.exceptions.ConnectionError,
            ),
            patch.object(gui.time, "sleep", side_effect=AssertionError("retried")),
            patch.object(gui.webview, "create_window") as create_window,
            patch.object(gui.webview, "start") as start,
            patch.object(gui, "LOGGER"),
        ):
            gui.main()

        create_window.assert_not_called()
        start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
