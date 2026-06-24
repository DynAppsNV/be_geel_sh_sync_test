from .common import VoipHelpdeskCommon


class TestResPartner(VoipHelpdeskCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_partner = cls.env['res.partner'].create({
            "name": "Company of Customer Credee",
        })
        cls.partner.parent_id = cls.company_partner

    def test_ticket_count(self):
        self.assertEqual(self.partner.ticket_count, 5, "The ticket count should be 5 for the partner.")
        self.assertEqual(self.company_partner.ticket_count, 5, "The ticket count should be 5 for the parent partner.")

    def test_open_ticket_count(self):
        self.assertEqual(self.partner.open_ticket_count, 3, "The open ticket count should be 3 for the partner.")
        self.assertEqual(self.company_partner.open_ticket_count, 3, "The open ticket count should be 3 for the parent partner.")
