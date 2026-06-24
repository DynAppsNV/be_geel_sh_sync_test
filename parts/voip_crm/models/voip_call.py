from odoo import fields, models


class VoipCall(models.Model):
    _inherit = "voip.call"

    opportunity_count = fields.Integer(related="partner_id.opportunity_count", groups="sales_team.group_sale_salesman", related_sudo=False)

    def voip_action_view_opportunity(self):
        action = self.partner_id.action_view_opportunity()
        if not self.partner_id:
            action["context"] = {
                "default_phone": self.phone_number,
            }
        return action
