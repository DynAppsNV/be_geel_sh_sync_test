from odoo import fields, models


class VoipCall(models.Model):
    _inherit = "voip.call"

    subscription_count = fields.Integer(related="partner_id.subscription_count", groups="sales_team.group_sale_salesman", related_sudo=False)

    def voip_action_open_subscription(self):
        self.ensure_one()
        return self.partner_id.open_related_subscription()
