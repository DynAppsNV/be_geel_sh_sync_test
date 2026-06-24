from odoo import models, api


class PosPrepOrder(models.Model):
    _inherit = 'pos.prep.order'

    @api.model
    def process_order(self, order_id, options={}):
        """Override to send order received notification via SMS/WhatsApp."""
        if not order_id or not self.env['pos.order'].browse(order_id).exists():
            return

        order = self.env['pos.order'].browse(order_id)
        existing_prep_orders = self.env['pos.prep.order'].search([('pos_order_id', '=', order.id)])

        result = super().process_order(order_id, options)

        new_prep_orders = self.env['pos.prep.order'].search([('pos_order_id', '=', order.id)])
        prep_orders_added = new_prep_orders and not existing_prep_orders

        # Send notification ONLY when prep orders are first created, not on subsequent calls.
        # prep_orders_added is True when the prep orders are created for the first time to avoid sending multiple notifications to user phone number.
        # it can be called two times with an online pm set.
        if prep_orders_added and not options.get('cancelled') and order.partner_id and order.partner_id.phone:
            category_ids = new_prep_orders.prep_line_ids.product_id.pos_categ_ids.ids
            for p_dis in self.env['pos.prep.display']._get_preparation_displays(order, category_ids):
                p_dis.send_order_notifications(order, 'received')

        return result
