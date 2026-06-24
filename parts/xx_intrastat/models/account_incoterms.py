from odoo import fields, models


class AccountIncoterms(models.Model):
    _inherit = "account.incoterms"

    xx_default_incoterm = fields.Boolean(help="Default Incoterm to apply when for vendor bills.")
