# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = "pos.config"

    def notify_platform_order_synchronisation(self, order, is_new_order=False):
        """
        Notify the PoS that a platoform order needs to be synchronised.
        """
        self.ensure_one()
        if not self.current_session_id:
            _logger.warning("Trying to notify a platform order synchronisation on a PoS without an open session (PoS: %s)", self.name)
            return
        self._notify('PLATFORM_ORDER_SYNCHRONISATION', {'order_id': order.id, 'is_new_order': is_new_order})
