# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ae_employer_code = fields.Char(string="Employer Unique ID")
    l10n_ae_bank_account_id = fields.Many2one(
        "res.partner.bank",
        domain="[('bank_id.country.code', '=', 'AE'), ('partner_id', '=', partner_id)]",
        string="Salaries Bank Account",
    )

    _l10n_ae_unique_l10n_ae_employer_code = models.Constraint(
        'UNIQUE(l10n_ae_employer_code)',
        "UAE Employeer ID must be unique.",
    )

    @api.constrains('l10n_ae_employer_code')
    def _check_l10n_ae_employer_code(self):
        if any(company.l10n_ae_employer_code and not company.l10n_ae_employer_code.isdigit() for company in self):
            raise ValidationError(_("The Employer Unique ID must contain only digits."))
