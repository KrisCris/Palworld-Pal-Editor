"""No REST route answers a traceback just because no save is open yet (spec §8.7).

§8.7 keeps `500` for unexpected exceptions, and a session with nothing loaded is
not one: it is the state every run starts in, the state the entry page sits in,
and the state a failed `open()` deliberately resets back to. Yet the reads that
walk base camps or containers reached `camp_data`/`container_data` while both
were still None, so `GET /api/rosters`, `/api/storages` and four others came back
`500 UNEXPECTED_ERROR` carrying a server traceback -- the same class of leak
`test_rest_auth_rejection` covers for a caller with no token.

`SaveManager` already answers this state emptily where it was asked to: a reset
`get_players()` returns `[]` off an empty repository. These routes now say the
same thing, so an unloaded session reads as empty rather than broken.

As in the auth test, the route list is read out of the app, so a route added
later is covered the day it is added.
"""

import re
import unittest

from flask_jwt_extended import create_access_token

from palworld_pal_editor.core import SaveManager
from palworld_pal_editor.webui import app


PUBLIC_ROUTES = {
    ("GET", "/api/ready"),
    ("GET", "/api/app-config"),
    ("POST", "/api/auth/login"),
}

# Writes are excluded: what they do to an empty session is each route's own
# business, and several legitimately refuse a request this test would have to
# invent a body for. What is checked here is that reading an empty session is
# not an error.
_PARAMETER = re.compile(r"<(?:[^:<>]+:)?[^<>]+>")


def _readable_routes() -> list[str]:
    paths = []
    for rule in sorted(app.url_map.iter_rules(), key=str):
        template = str(rule)
        if not template.startswith("/api") or "GET" not in rule.methods:
            continue
        if ("GET", template) in PUBLIC_ROUTES:
            continue
        paths.append(_PARAMETER.sub("1", template))
    return paths


class NoSaveLoadedRestTests(unittest.TestCase):
    def setUp(self):
        # The condition under test is the real manager in the state `reset()`
        # leaves it, which is also the state it starts in, so no fake stands in.
        SaveManager().reset()
        self.client = app.test_client()
        app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        with app.app_context():
            token = create_access_token(identity="test", expires_delta=False)
        self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        SaveManager().reset()

    def test_no_read_answers_a_traceback_with_no_save_open(self):
        paths = _readable_routes()
        self.assertTrue(paths, "the app registered no readable routes to check")
        for path in paths:
            with self.subTest(route=path):
                response = self.client.get(path, headers=self.headers)
                body = response.get_data(as_text=True)
                self.assertNotEqual(response.status_code, 500, body[:400])
                self.assertNotIn("Traceback", body)
                self.assertNotIn("UNEXPECTED_ERROR", body)

    def test_an_unloaded_session_reads_as_empty_rather_than_missing(self):
        """The lists exist and are empty; they are not 404s for absent resources."""
        for path in (
            "/api/players",
            "/api/rosters",
            "/api/storages",
            "/api/rosters/base-workers/pals",
            "/api/rosters/global-palbox/pals",
        ):
            with self.subTest(route=path):
                response = self.client.get(path, headers=self.headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json(), [])

    def test_naming_something_no_empty_session_holds_is_still_a_404(self):
        for path in (
            "/api/players/1",
            "/api/players/1/inventory",
            "/api/pals/world:1",
            "/api/storages/world-container:1",
            "/api/rosters/player:1/pals",
        ):
            with self.subTest(route=path):
                response = self.client.get(path, headers=self.headers)
                self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
