from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestResPartnerSync(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user = self.env.user

        self.currency = self.env.ref("base.USD")

    @patch("odoo.addons.xx_horizon.models.xx_sync_record.SyncRecord.queue")
    def test_create_triggers_queue(self, mock_queue):
        partner_vals = {
            "name": "Test Partner",
            "active": True,
            "street": "123 Main St",
            "zip": "12345",
            "city": "Testville",
            "currency_id": self.currency.id,
        }

        partner = self.env["res.partner"].create([partner_vals])[0]

        self.assertTrue(mock_queue.called)
        call_args = mock_queue.call_args[1]
        self.assertEqual(call_args["model"], "res.partner")
        payload = call_args["payload"]
        self.assertEqual(payload["Contact_ID"], partner.id)
        self.assertEqual(payload["Name_1"], partner.name)

    @patch("odoo.addons.xx_horizon.models.xx_sync_record.SyncRecord.queue")
    def test_write_triggers_queue_for_relevant_fields(self, mock_queue):
        partner = self.env["res.partner"].create(
            [
                {
                    "name": "Partner 2",
                    "currency_id": self.currency.id,
                }
            ]
        )[0]

        mock_queue.reset_mock()

        partner.write({"name": "Partner 2 Updated"})
        self.assertTrue(mock_queue.called)
        payload = mock_queue.call_args[1]["payload"]
        self.assertEqual(payload["Name_1"], "Partner 2 Updated")

        mock_queue.reset_mock()
        partner.write({"comment": "This is irrelevant"})
        self.assertFalse(mock_queue.called)

    @patch("odoo.addons.xx_horizon.models.xx_sync_record.SyncRecord.queue")
    def test_unlink_triggers_queue(self, mock_queue):
        partner = self.env["res.partner"].create(
            [
                {
                    "name": "Partner 3",
                    "currency_id": self.currency.id,
                }
            ]
        )[0]

        partner.unlink()
        self.assertTrue(mock_queue.called)
        payload = mock_queue.call_args[1]["payload"]
        self.assertEqual(payload["Contact_ID"], partner.id)
