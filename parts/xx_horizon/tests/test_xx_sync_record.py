import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from odoo.tests.common import TransactionCase


class TestSyncRecord(TransactionCase):
    def setUp(self):
        super().setUp()

        self.user = self.env.user

        self.env["ir.config_parameter"].sudo().set_param(
            "xx_horizon.pas_base_url", "http://localhost"
        )

    def test_queue_creates_record(self):
        payload = {"foo": "bar"}
        record = self.env["xx.sync.record"].queue(
            env=self.env,
            model="xx.credit.line",
            payload=payload,
            endpoint="creditlimit",
            method="POST",
        )

        self.assertEqual(record.model_name, "xx.credit.line")
        self.assertEqual(record.endpoint, "creditlimit")
        self.assertEqual(record.method, "POST")
        self.assertEqual(record.user_login, self.user.login)

        content = json.loads(record.content)
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["foo"], "bar")
        self.assertFalse(record.synced)

    @patch("odoo.addons.xx_horizon.models.xx_sync_record.requests.post")
    @patch("odoo.addons.xx_horizon.models.xx_sync_record.SyncRecord.get_pas_token")
    def test_process_unsynced_records_post_success(self, mock_token, mock_post):
        mock_token.return_value.token = "abc123"

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"
        mock_post.return_value = mock_resp

        record = self.env["xx.sync.record"].create(
            {
                "user_login": self.user.login,
                "model_name": "xx.credit.line",
                "endpoint": "creditlimit",
                "method": "POST",
                "content": json.dumps([{"foo": "bar"}]),
                "synced": False,
            }
        )

        record.with_context(skip_commit=True)._process_batch()

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("http://localhost/creditlimit", args)
        payload = kwargs["json"]
        self.assertIn("data", payload)
        self.assertEqual(payload["data"][0]["foo"], "bar")
        self.assertEqual(payload["data"][0]["ModifyUser"], self.user.login)

        record = self.env["xx.sync.record"].browse(record.id)
        self.assertTrue(record.synced)
        self.assertEqual(record.response_message, "200: ok")
        self.assertIsNotNone(record.sync_date)

    @patch("odoo.addons.xx_horizon.models.xx_sync_record.SyncRecord.get_pas_token")
    def test_process_unsynced_records_exception(self, mock_token):
        mock_token.side_effect = ValueError("token error")

        record = self.env["xx.sync.record"].create(
            {
                "user_login": self.user.login,
                "model_name": "xx.credit.line",
                "endpoint": "creditlimit",
                "method": "POST",
                "content": json.dumps([{"foo": "bar"}]),
                "synced": False,
            }
        )

        record.with_context(skip_commit=True)._process_batch()

        record = self.env["xx.sync.record"].browse(record.id)
        self.assertFalse(record.synced)
        self.assertIn("token error", record.response_message)

    def test_parse_token_response(self):
        sr = self.env["xx.sync.record"]
        now = datetime.now(timezone.utc)
        response_json = {"access_token": "abc", "expires_in": 3600, "token_type": "Bearer"}
        token_obj = sr.parse_token_response(response_json)
        self.assertEqual(token_obj.token, "abc")
        self.assertEqual(token_obj.token_type, "Bearer")
        self.assertTrue(token_obj.expires_at > now)
