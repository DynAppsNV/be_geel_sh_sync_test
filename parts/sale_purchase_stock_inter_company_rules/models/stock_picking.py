# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        res = super().button_validate()
        move_line_ids_to_delete = []
        move_line_vals_to_create = []
        for picking in self:
            if not picking.sale_id or picking.picking_type_code not in ('outgoing', 'dropship'):
                continue
            company_rec = self.env['res.company']._find_company_from_partner(picking.sudo().sale_id.partner_id.id)
            if company_rec and company_rec.intercompany_sync_delivery_receipt:
                # Fetch linked Sale Order
                sale_order = picking.sale_id
                purchase_order = self.env['purchase.order'].sudo().search([('name', '=', sale_order.client_order_ref), ('company_id', '=', company_rec.id)])
                # Find corresponding receipt in other company
                receipts = purchase_order.picking_ids.filtered(lambda p: p.picking_type_code in ('incoming', 'dropship'))
                if not receipts:
                    continue
                assigned_move_ids = set()
                for move in picking.move_ids:
                    if move.state != 'done' or move.product_id.company_id:
                        continue
                    find_ctx = {"assigned_move_ids": assigned_move_ids, "skip_price_check": False}
                    receipt_move = picking.with_context(**find_ctx)._find_corresponding_move(move, receipts)
                    if not receipt_move:  # Try again without checking the price in case it was changed
                        find_ctx["skip_price_check"] = True
                        receipt_move = picking.with_context(**find_ctx)._find_corresponding_move(move, receipts)
                    if receipt_move:
                        move_line_ids_to_delete.extend(receipt_move.move_line_ids.ids)
                        move_line_vals_to_create.extend(self._prepare_move_lines(move, receipt_move))
        move_lines_to_delete = self.env['stock.move.line'].browse(move_line_ids_to_delete)
        move_lines_to_delete.sudo().unlink()
        if move_line_vals_to_create:
            new_lines = self.env['stock.move.line'].sudo().create(move_line_vals_to_create)
            new_lines._apply_putaway_strategy()
        return res

    @api.model
    def _find_corresponding_move(self, move_orig, candidate_pickings):
        price_precision = self.env["decimal.precision"].precision_get("Product Price")
        assigned_move_ids = self.env.context.get("assigned_move_ids", set())
        skip_price_check = self.env.context.get("skip_price_check", False)
        for receipt_move in candidate_pickings.move_ids:
            if receipt_move.id in assigned_move_ids or receipt_move.picked or not receipt_move.purchase_line_id:
                continue
            purchase_price = receipt_move.purchase_line_id.price_unit or 0.0
            converted_sale_price = move_orig.sale_line_id.product_uom_id._compute_price(
                move_orig.sale_line_id.price_unit or 0.0, receipt_move.purchase_line_id.product_uom_id
            )
            if (
                receipt_move.product_id == move_orig.product_id
                and receipt_move.product_uom == move_orig.product_uom
                and (
                    skip_price_check
                    or float_compare(purchase_price, converted_sale_price, precision_digits=price_precision) == 0
                )
            ):
                assigned_move_ids.add(receipt_move.id)
                return receipt_move
        return False

    @api.model
    def _prepare_move_lines(self, delivery_move, receipt_move):
        move_lines_vals = []
        for move_line in delivery_move.move_line_ids:
            ml_vals = receipt_move._prepare_move_line_vals(quantity=0)
            if move_line.lot_id:
                ml_vals['lot_name'] = move_line.lot_id.name
                if not move_line.lot_id.company_id:
                    ml_vals['lot_id'] = move_line.lot_id.id
            ml_vals['quantity'] = move_line.quantity
            ml_vals['picked'] = True
            move_lines_vals.append(ml_vals)
        return move_lines_vals
