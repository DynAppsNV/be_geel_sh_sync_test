from odoo import models, _
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _check_cashier_l10n_be_insz_or_bis_number(self):
        super()._check_cashier_l10n_be_insz_or_bis_number()
        for config in self:
            if config.module_pos_hr:
                all_employee_ids = self.env['hr.employee'].search(self._employee_domain(self.env.uid))
                missing_employees = [emp.name for emp in all_employee_ids if not emp.sudo().l10n_be_insz_or_bis_number]
                if len(missing_employees) > 0:
                    count = len(missing_employees)
                    employee_label = "employee" if count == 1 else "employees"
                    raise ValidationError(
                        _(
                            "%(employees)s (%(label)s) must have an INSZ or BIS number.",
                            employees=", ".join(missing_employees),
                            label=employee_label,
                        )
                    )
