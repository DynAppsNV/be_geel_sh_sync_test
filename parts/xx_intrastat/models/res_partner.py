from odoo import fields, models


class InheritedPartner(models.Model):
    _inherit = "res.partner"

    xx_commodity_code_id = fields.Many2one(
        string="Default Commodity",
        comodel_name="account.intrastat.code",
        domain=lambda self: [
            ("type", "=", "commodity"),
            "&",
            "|",
            ("expiry_date", ">", fields.Date.context_today(self)),
            ("expiry_date", "=", False),
            "|",
            ("start_date", "<=", fields.Date.context_today(self)),
            ("start_date", "=", False),
        ],
        required=False,
    )
