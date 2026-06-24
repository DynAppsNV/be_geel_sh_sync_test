from odoo import models
from odoo.exceptions import ValidationError

from odoo.addons.module_change_auto_install.patch import _get_modules_auto_install_disabled_dict


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def button_install(self):
        for module in self:
            if module.name in _get_modules_auto_install_disabled_dict().keys():
                raise ValidationError(
                    self.env._(
                        "Module '%(module_name)s' is set to be disabled by "
                        "module_change_auto_install configuration and cannot be installed.",
                        module_name=module.name,
                    )
                )
        return super().button_install()
