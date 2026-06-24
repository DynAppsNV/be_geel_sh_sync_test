from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        res.append(self.env.ref('esg_csrd.menu_esg_csrd_config').id)
        return res
