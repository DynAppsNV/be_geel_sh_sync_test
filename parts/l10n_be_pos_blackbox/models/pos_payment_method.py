from odoo import models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_mapped_payment_type(self):
        """ Returns the payment type mapped for blackbox purposes. """
        self.ensure_one()
        type_map = {
            'cash': 'CASH',
            'bank': 'CARD_UNKNOWN',
            'pay_later': 'CUSTOMER_CREDIT',
            'online': 'ONLINE',
        }
        return type_map.get(self.type, "OTHER")
