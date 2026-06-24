import json
from http import HTTPStatus

from odoo.tests.common import HttpCase, mute_logger


class TestAnalyticsController(HttpCase):
    def test_01_json(self):
        self.authenticate("admin", "admin")
        body = json.dumps({})
        response = self.url_open("/.dynapps/analytics", data=body)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        payload = response.json()
        self.assertIn("odoo_version", payload)
        self.assertIn("database_uuid", payload)
        self.assertIn("modules", payload)
        self.assertIsInstance(payload["modules"], dict)
        self.assertIn("dyn_analytics", payload["modules"])

    @mute_logger("odoo.http")
    def test_02_json_access_denied(self):
        self.authenticate("demo", "demo")
        headers = {
            "Content-Type": "application/json",
        }
        body = json.dumps({})

        response = self.url_open("/.dynapps/analytics", headers=headers, data=body)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
