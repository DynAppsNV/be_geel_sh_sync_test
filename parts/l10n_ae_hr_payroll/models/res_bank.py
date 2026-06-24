# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResBank(models.Model):
    _inherit = 'res.bank'

    l10n_ae_routing_code = fields.Char(string="UAE Routing Code Agent ID")

    @api.constrains('l10n_ae_routing_code')
    def _check_l10n_ae_routing_code(self):
        if any(bank.l10n_ae_routing_code and (len(bank.l10n_ae_routing_code) != 9 or not bank.l10n_ae_routing_code.isdigit()) for bank in self):
            raise ValidationError(_("UAE Routing Code Agent ID should be 9 digits only."))
