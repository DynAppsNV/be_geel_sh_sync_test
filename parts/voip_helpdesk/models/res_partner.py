from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    ticket_ids = fields.One2many("helpdesk.ticket", "partner_id")
    open_ticket_count = fields.Integer(compute="_compute_open_ticket_count", groups="helpdesk.group_helpdesk_user")

    @api.depends("ticket_ids.fold")
    def _compute_open_ticket_count(self):
        count_by_partner_id = self._count_tickets_by_partner_id(
            extra_domain=[("fold", "=", False)],
        )
        for partner in self:
            partner.open_ticket_count = count_by_partner_id.get(partner.id, 0)
