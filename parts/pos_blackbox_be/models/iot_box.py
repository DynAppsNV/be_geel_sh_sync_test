# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class IotBox(models.Model):
    _inherit = 'iot.box'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active_pos_blackbox(self):
        for box in self:
            if box.device_ids and self.env['pos.config'].sudo().search_count([('iface_fiscal_data_module', 'in', box.device_ids.ids)], limit=1):
                raise UserError(_("Before unlinking the IOT box from your database, ensure that the blackbox is not used in your POS."))
