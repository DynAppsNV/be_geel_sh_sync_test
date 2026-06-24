from odoo.tests import users

from .common import VoipHelpdeskCommon


class TestVoipCall(VoipHelpdeskCommon):
    @users("user_helpdesk_user")
    def test_voip_call_ticket_count_user(self):
        partner = self.partner.with_env(self.env)
        call = self.call_1.with_env(self.env)
        self.assertEqual([partner.ticket_count, partner.open_ticket_count], [call.ticket_count, call.open_ticket_count],
                         "The ticket counts on the call should match those on the partner.")

    @users("user_helpdesk_manager")
    def test_voip_call_ticket_count_manager(self):
        partner = self.partner.with_env(self.env)
        call = self.call_2.with_env(self.env)
        self.assertEqual([partner.ticket_count, partner.open_ticket_count], [call.ticket_count, call.open_ticket_count],
                         "The ticket counts on the call should match those on the partner.")
