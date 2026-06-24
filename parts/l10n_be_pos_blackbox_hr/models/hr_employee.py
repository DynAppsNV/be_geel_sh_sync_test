from odoo.exceptions import ValidationError
from odoo import models, fields, api
from odoo.tools.translate import _


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_be_insz_or_bis_number = fields.Char("INSZ or BIS number", help="Belgian National Register number")
    pos_clock_in_out_ids = fields.One2many('pos.clock.in.out', 'employee_id', string='POS Clock In/Out Events')

    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['l10n_be_insz_or_bis_number']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            user_id = vals.get("user_id")
            if user_id and not vals.get("l10n_be_insz_or_bis_number"):
                user = self.env["res.users"].browse(user_id)
                if user.l10n_be_insz_or_bis_number:
                    vals["l10n_be_insz_or_bis_number"] = user.l10n_be_insz_or_bis_number
        return super().create(vals_list)

    @api.constrains("l10n_be_insz_or_bis_number")
    def _check_l10n_be_insz_or_bis_number(self):
        for emp in self:
            insz_number = emp.l10n_be_insz_or_bis_number
            if insz_number and not self.env['res.users'].is_valid_l10n_be_insz_or_bis_number(insz_number):
                raise ValidationError(_("The Belgian National Register Number is not valid."))
