"""No REST route answers a caller who has no valid token, per spec §12.

`register_error_handlers` gives every blueprint a catch-all so an unexpected
exception still comes back as §8.7's envelope rather than an HTML error page. A
blueprint handler shadows an app-level one, so that catch-all was also claiming
the JWT failures `webui.py`'s `@jwt` loaders exist to answer: a request with no
token, an expired one or a malformed one came back as `500 UNEXPECTED_ERROR`
with a server traceback in the body. Two things were wrong with that. The
frontend decides to ask for the password again on `httpStatus === 401` alone
(`api/http.js`), so an expired session showed a generic failure instead of the
login prompt; and an unauthenticated caller got absolute filesystem paths back
from software whose README supports remote access.

The route list is read out of the app rather than written down here, so a route
added later is covered the day it is added, and making one public has to be a
deliberate edit to `PUBLIC_ROUTES` instead of an oversight nobody sees.
"""

import re
import unittest
from datetime import timedelta
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from palworld_pal_editor.utils import DataProvider
from palworld_pal_editor.webui import app


# The routes that answer before there is a token to answer with: the liveness
# probe, the bootstrap read the login screen itself needs, and the route that
# issues the token. Whether login accepts a given password is auth's own business.
PUBLIC_ROUTES = {
    ("GET", "/api/ready"),
    ("GET", "/api/app-config"),
    ("POST", "/api/auth/login"),
}

_PARAMETER = re.compile(r"<(?:[^:<>]+:)?[^<>]+>")


def _guarded_routes() -> list[tuple[str, str]]:
    """Every `/api` route that is not public, with its parameters filled in.

    The value put in a parameter does not matter: the token is checked before the
    route looks at anything, so a key that names nothing is refused the same way.
    """
    routes = []
    for rule in sorted(app.url_map.iter_rules(), key=str):
        template = str(rule)
        if not template.startswith("/api"):
            continue
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            if (method, template) not in PUBLIC_ROUTES:
                routes.append((method, _PARAMETER.sub("1", template)))
    return routes


class UnauthenticatedRestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
        with app.app_context():
            cls.token = create_access_token(identity="test", expires_delta=False)
            cls.expired = create_access_token(
                identity="test", expires_delta=timedelta(seconds=-1)
            )

    def setUp(self):
        self.client = app.test_client()

    def test_no_route_serves_a_caller_who_sent_no_token(self):
        routes = _guarded_routes()
        self.assertTrue(routes, "the app registered no guarded routes to check")
        for method, path in routes:
            with self.subTest(route=f"{method} {path}"):
                response = self.client.open(path, method=method)
                body = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 401)
                # Refused, and refused without telling the caller where the
                # server keeps its files or pretending this was a server fault.
                self.assertNotIn("Traceback", body)
                self.assertNotIn("UNEXPECTED_ERROR", body)

    def test_an_expired_token_is_refused_the_way_a_missing_one_is(self):
        """The case the user actually meets: the tab was left open overnight."""
        response = self.client.get(
            "/api/rosters", headers={"Authorization": f"Bearer {self.expired}"}
        )
        self.assertEqual(response.status_code, 401)

    def test_a_token_that_is_not_a_token_is_refused_too(self):
        response = self.client.get(
            "/api/rosters", headers={"Authorization": "Bearer not-a-token"}
        )
        self.assertEqual(response.status_code, 401)

    def test_the_reads_the_login_screen_needs_still_answer_without_a_token(self):
        for path in ("/api/ready", "/api/app-config"):
            with self.subTest(route=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_an_unexpected_failure_still_comes_back_as_the_envelope(self):
        """Auth was carved out of the catch-all, not carved into it."""
        with patch.object(
            DataProvider, "get_sorted_passives", side_effect=RuntimeError("boom")
        ):
            response = self.client.get(
                "/api/catalogs/skills",
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "UNEXPECTED_ERROR")


if __name__ == "__main__":
    unittest.main()
