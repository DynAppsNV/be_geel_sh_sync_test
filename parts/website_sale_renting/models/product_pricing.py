# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductPricing(models.Model):
    _inherit = 'product.pricing'

    def _get_tz(self):
        if website := self.env["website"].get_current_website(fallback=False):
            return website.tz
        return super()._get_tz()
