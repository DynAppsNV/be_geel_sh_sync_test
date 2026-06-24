from odoo import models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def _blackbox_uninstall_error(self, module_name, bbox_pos_config, replace_by=None):
        message = _(
            "The module '%(module_name)s' cannot be uninstalled because a Blackbox PoS configuration is still active.\n"
            "Blocking PoS configuration: %(configs)s"
        ) % {
            'module_name': module_name,
            'configs': ", ".join(bbox_pos_config.mapped("name")),
        }

        if replace_by:
            message += _(
                "\n\nIf you want to remove this functionality, please uninstall the '%(replace_by)s' module instead."
            ) % {'replace_by': replace_by}

        return UserError(message)

    def module_uninstall(self):
        bbox_pos_config = self.env['pos.config'].search([('l10n_be_blackbox_be_id', '!=', False)], limit=1)
        if bbox_pos_config:
            modules_to_remove = self.mapped('name')
            if (module := self.filtered(lambda m: m.name == "l10n_be_pos_blackbox")):
                raise self._blackbox_uninstall_error(module.shortdesc, bbox_pos_config)
            elif (module := self.filtered(lambda m: m.name == "l10n_be_pos_blackbox_settle_due")) and "pos_settle_due" not in modules_to_remove:
                raise self._blackbox_uninstall_error(module.shortdesc, bbox_pos_config, replace_by="pos_settle_due")
            elif (module := self.filtered(lambda m: m.name == "l10n_be_pos_blackbox_loyalty")) and "pos_loyalty" not in modules_to_remove:
                raise self._blackbox_uninstall_error(module.shortdesc, bbox_pos_config, replace_by="pos_loyalty")
            elif (module := self.filtered(lambda m: m.name == "l10n_be_pos_blackbox_self_order")) and "pos_self_order" not in modules_to_remove:
                raise self._blackbox_uninstall_error(module.shortdesc, bbox_pos_config, replace_by="pos_self_order")
            elif (module := self.filtered(lambda m: m.name == "l10n_be_pos_blackbox_urban_piper")) and "pos_urban_piper" not in modules_to_remove:
                raise self._blackbox_uninstall_error(module.shortdesc, bbox_pos_config, replace_by="pos_urban_piper")
            elif (module := self.filtered(lambda m: m.name == "l10n_be_pos_blackbox_hr")) and "pos_hr" not in modules_to_remove:
                raise self._blackbox_uninstall_error(module.shortdesc, bbox_pos_config, replace_by="pos_hr")
        return super().module_uninstall()
