from odoo import models


class PosPreparationState(models.Model):
    _inherit = 'pos.prep.state'

    def change_state_stage(self, stages, prep_display_id):
        """Override to send order ready notification via SMS/WhatsApp."""
        result = super().change_state_stage(stages, prep_display_id)

        # Track orders we've notified to avoid duplicates
        notified_orders = set()
        prep_display = self.env['pos.prep.display'].browse(prep_display_id)

        # Send notification when order reaches second last stage (ready)
        for pdis_state in self:
            if pdis_state.stage_id.is_stage_position(-2):
                order = pdis_state.prep_line_id.pos_order_line_id.order_id
                if order and order.id not in notified_orders and order.partner_id and order.partner_id.phone:
                    prep_display.send_order_notifications(order, 'ready')
                    notified_orders.add(order.id)

        return result
