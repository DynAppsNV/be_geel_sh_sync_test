from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.base.models.ir_module import IrModuleModule


# pylint: disable=R8180
# Python inheritance of the module is necessary to inherit @staticmethod methods
class IrModuleStaticMethod(IrModuleModule):
    _inherit = "ir.module.module"

    @staticmethod
    def get_values_from_terp(terp):
        res = super(IrModuleStaticMethod, IrModuleStaticMethod).get_values_from_terp(terp)
        res["dyn_required"] = terp.get("dyn_required", False)
        return res


class IrModule(models.Model):
    _inherit = "ir.module.module"

    dyn_required = fields.Boolean()
    dyn_required_dependency = fields.Boolean(
        compute="_compute_required_dependency",
        help="A (indirect) dependency is required or "
        "a required installed module needs this module.",
    )

    def _compute_required_dependency(self):
        for rec in self:
            dependencies = rec
            # Search all installed modules that (indirectly) require this module
            dependencies |= rec.downstream_dependencies(exclude_states=("uninstalled",))
            rec.dyn_required_dependency = any(map(lambda m: m.dyn_required, dependencies))

    def button_uninstall(self):
        if any(map(lambda x: x.dyn_required_dependency, self)):
            raise UserError(self.env._("Uninstalling a Dynapps required module is not possible."))
        return super().button_uninstall()

    def module_uninstall(self):
        if any(map(lambda x: x.dyn_required_dependency, self)):
            raise UserError(self.env._("Uninstalling a Dynapps required module is not possible."))
        return super().module_uninstall()
