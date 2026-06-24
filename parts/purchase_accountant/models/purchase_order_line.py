from odoo import api, fields, models
from odoo.tools import split_every
from dateutil.relativedelta import relativedelta


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_categ_id = fields.Many2one(related='product_id.categ_id')

    prepaid_expense = fields.Boolean(
        string='Prepaid Expense', search="_search_prepaid_expense",
        store=False)
    bill_to_receive = fields.Boolean(
        string='Bill to Receive', search="_search_bill_to_receive",
        store=False)

    def _search_prepaid_expense(self, operator, value):
        if operator != 'in':
            return NotImplemented
        return [('id', 'in', self._get_accrual_line_ids('prepaid'))]

    def _search_bill_to_receive(self, operator, value):
        if operator != 'in':
            return NotImplemented
        return [('id', 'in', self._get_accrual_line_ids('bill_to_receive'))]

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None) -> list[tuple]:
        return self._read_group_for_accrual(domain, groupby, aggregates, having, offset, limit, order)

    @api.model
    def _get_accrual_line_ids(self, mode):
        result_ids = []

        po_lines = self.env['purchase.order.line'].search_fetch(
            self._get_accrual_domain(),
            ['qty_invoiced_at_date', 'qty_received_at_date'],
            order='id',
        )

        for lines in split_every(5000, po_lines):
            for line in lines:
                if mode == 'prepaid':
                    if (line.qty_invoiced_at_date and line.qty_invoiced_at_date > line.qty_received_at_date):
                        result_ids.append(line.id)
                elif mode == 'bill_to_receive':
                    if (line.qty_received_at_date and line.qty_invoiced_at_date < line.qty_received_at_date):
                        result_ids.append(line.id)
                else:
                    raise ValueError('Invalid accrual mode')
        return result_ids

    @api.model
    def _get_accrual_domain(self):
        accrual_date = self.env.context.get('accrual_entry_date')
        ref_date = fields.Date.to_date(accrual_date) if accrual_date else fields.Date.context_today(self)
        date_from = ref_date - relativedelta(years=1)
        domain = [
            ('product_id', '!=', False),
            ('state', '=', 'purchase'),
            ('order_id.date_order', '>=', date_from),
            ('order_id.date_order', '<=', ref_date),
        ]
        return domain

    @api.model
    def _get_aggregates_to_skip_and_fields_to_patch(self):
        aggregates_to_skip, fields_to_patch = super()._get_aggregates_to_skip_and_fields_to_patch()
        aggregates_to_skip.insert(0, 'qty_received_at_date:sum')
        fields_to_patch.insert(0, 'qty_received_at_date')
        return (aggregates_to_skip, fields_to_patch)
