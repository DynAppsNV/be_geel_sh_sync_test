from odoo import fields, models, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    rewarded_product_id = fields.Many2one("product.product", string="Rewarded Product")

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['rewarded_product_id']
        return params
