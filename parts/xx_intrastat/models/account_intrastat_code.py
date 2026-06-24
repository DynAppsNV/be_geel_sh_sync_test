from odoo import fields, models


class AccountIntrastatCode(models.Model):
    _inherit = "account.intrastat.code"

    xx_default_transport = fields.Boolean(help="Default transport mode to apply for vendor bills.")

    xx_default_transaction = fields.Boolean(
        help="Default Transaction to apply when for vendor bills."
    )
