from odoo.exceptions import ValidationError
from odoo import models, fields, api
from odoo.tools.translate import _


class ResUsers(models.Model):
    _inherit = "res.users"

    l10n_be_insz_or_bis_number = fields.Char("INSZ or BIS number", help="Belgian National Register number")
    pos_clock_in_out_ids = fields.One2many('pos.clock.in.out', 'user_id', string='POS Clock In/Out Events')

    @api.model
    def _load_pos_data_fields(self, config):
        result = super()._load_pos_data_fields(config)
        if config.l10n_be_blackbox_be_id:
            result += ['l10n_be_insz_or_bis_number']
        return result

    @api.constrains("l10n_be_insz_or_bis_number")
    def _check_l10n_be_insz_or_bis_number(self):
        for emp in self:
            insz_number = emp.l10n_be_insz_or_bis_number
            if insz_number and not emp.is_valid_l10n_be_insz_or_bis_number(insz_number):
                raise ValidationError(_("The National Register Number is not valid."))

    @api.model
    def is_valid_l10n_be_insz_or_bis_number(self, number):
        if not number:
            return False
        if len(number) != 11 or not number.isdigit():
            return False

        partial_number = number[:-2]
        modulo = int(partial_number) % 97

        if modulo == 97 - int(number[-2:]):
            return True

        # Allow employee and user born after 2000.
        partial_number = '2' + partial_number
        modulo = int(partial_number) % 97

        return modulo == 97 - int(number[-2:])
