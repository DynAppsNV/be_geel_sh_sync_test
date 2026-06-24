from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from odoo.tools import split_every


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_invoice_policy = fields.Selection(related='product_id.invoice_policy')

    deferred_revenue = fields.Boolean(
        string='Deferred Revenue', search="_search_deferred_revenue",
        store=False)
    invoice_to_be_issued = fields.Boolean(
        string='Invoice to be Issued', search="_search_invoice_to_be_issued",
        store=False)

    def _search_deferred_revenue(self, operator, value):
        if operator != 'in':
            return NotImplemented
        return [('id', 'in', self._get_accrual_line_ids('deferred'))]

    def _search_invoice_to_be_issued(self, operator, value):
        if operator != 'in':
            return NotImplemented
        return [('id', 'in', self._get_accrual_line_ids('invoice_issued'))]

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None) -> list[tuple]:
        return self._read_group_for_accrual(domain, groupby, aggregates, having, offset, limit, order)

    @api.model
    def _get_accrual_line_ids(self, mode):
        result_ids = []
        so_lines = self.env['sale.order.line'].search_fetch(
            self._get_accrual_domain(),
            ['qty_invoiced', 'qty_delivered'],
            order='id',
        )
        for lines in split_every(5000, so_lines):
            for line in lines:
                if mode == 'deferred':
                    if line.qty_invoiced_at_date > line.qty_delivered_at_date:
                        result_ids.append(line.id)
                elif mode == 'invoice_issued':
                    if line.qty_invoiced_at_date < line.qty_delivered_at_date:
                        result_ids.append(line.id)
                else:
                    raise ValueError('Invalid accrual mode')
        return result_ids

    @api.model
    def _get_accrual_domain(self):
        accrual_date = self.env.context.get('accrual_entry_date')
        ref_date = (fields.Date.to_date(accrual_date) if accrual_date else fields.Date.context_today(self))
        date_from = ref_date - relativedelta(years=1)
        domain = [
            ('product_id', '!=', False),
            # A combo product line is a virtual parent with no delivery of its own; its delivered
            # quantity is never advanced, so it would always read as deferred. Its combo item
            # lines already carry the real delivery state, so exclude the parent to avoid listing
            # a line that is permanently "invoiced not delivered" and duplicating its items.
            ('product_id.type', '!=', 'combo'),
            ('state', '=', 'sale'),
            ('order_id.date_order', '>=', date_from),
            ('order_id.date_order', '<=', ref_date),
        ]
        return domain

    @api.model
    def _get_aggregates_to_skip_and_fields_to_patch(self):
        aggregates_to_skip, fields_to_patch = super()._get_aggregates_to_skip_and_fields_to_patch()
        aggregates_to_skip.insert(0, 'qty_delivered_at_date:sum')
        fields_to_patch.insert(0, 'qty_delivered_at_date')
        return (aggregates_to_skip, fields_to_patch)
