# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LazadaOrderItem(models.Model):
    """Lazada Order Item - Represents individual product items in Lazada orders.

    Each order item represents a single product unit. Multiple units of the same
    product create multiple order items.
    """

    _name = 'lazada.order.item'
    _description = 'Lazada Order Item'

    sale_order_line_id = fields.Many2one(
        'sale.order.line', ondelete='cascade', required=True, index=True
    )
    stock_move_id = fields.Many2one('stock.move', ondelete='cascade', index='btree_not_null')
    status = fields.Selection(
        help="The status of the order item on Lazada:\n"
        "- Draft: The order item is in draft status by default.\n"
        "- Confirmed: The order item has been packed.\n"
        "- Processing: The order item is ready to ship.\n"
        "- Delivered: The order item has been shipped or delivered.\n"
        "- Canceled: The order item has been canceled.\n"
        "- Manual: The order item has to be processed manually on Lazada.",
        selection=[
            ('draft', "Draft"),
            ('confirmed', "Confirmed"),
            ('processing', "Processing"),
            ('delivered', "Delivered"),
            ('canceled', "Canceled"),
            ('manual', "Manual"),
        ],
        required=True,
    )
    order_item_extern_id = fields.Char(string="Lazada Order Item ID", required=True)

    @api.constrains('sale_order_line_id', 'stock_move_id')
    def _check_stock_move(self):
        """Ensure stock move matches the sale order line."""
        for order_item in self:
            if (
                order_item.stock_move_id
                and order_item.stock_move_id.sale_line_id != order_item.sale_order_line_id
            ):
                raise ValidationError(
                    self.env._(
                        "The stock move must be related to the same sale order line as the Lazada"
                        " order item."
                    )
                )

    def write(self, vals):
        """Update order item and adjust sale order line quantity if canceled.

        :param dict vals: Values to write
        """
        if 'status' in vals:
            new_status = vals['status']
            diff_order_items = self.filtered(lambda order_item: order_item.status != new_status)
            for order_item in diff_order_items:
                if new_status == 'canceled':
                    if order_item.sale_order_line_id.order_id.locked:
                        order_item.sale_order_line_id.order_id.action_unlock()
                        order_item.sale_order_line_id.product_uom_qty = max(
                            order_item.sale_order_line_id.product_uom_qty - 1, 0
                        )
                        order_item.sale_order_line_id.order_id.action_lock()
                    else:
                        order_item.sale_order_line_id.product_uom_qty = max(
                            order_item.sale_order_line_id.product_uom_qty - 1, 0
                        )
        return super().write(vals)
