from odoo import _, models, api, fields
from odoo.exceptions import UserError


class ReportPoint_Of_SaleReport_Saledetails(models.AbstractModel):
    _inherit = "report.point_of_sale.report_saledetails"

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        before_closing = kwargs.pop("before_closing", False)
        data = super().get_sale_details(
            date_start, date_stop, config_ids, session_ids, **kwargs
        )

        if before_closing:
            data["state"] = "closed"
            data["date_stop"] = fields.Datetime.now()
        sessions = []
        configs = []
        if config_ids:
            configs = self.env['pos.config'].search([('id', 'in', config_ids)])
            if session_ids:
                sessions = self.env['pos.session'].search([('id', 'in', session_ids)])
            else:
                sessions = self.env['pos.session'].search([
                    ('config_id', 'in', configs.ids),
                    ('start_at', '>=', date_start),
                    ('stop_at', '<=', date_stop)
                ])
        else:
            sessions = self.env['pos.session'].search([('id', 'in', session_ids)])
            for session in sessions:
                configs.append(session.config_id)

        totalPaymentsAmount = 0
        for session in sessions:
            totalPaymentsAmount += session.total_payments_amount

        if len(sessions) == 1:
            session = sessions[0]
            config = session.config_id
            if config.l10n_be_blackbox_be_id:
                orders = self.env["pos.order"].search([
                    ("session_id", "=", session.id),
                    ('state', 'in', ['paid', 'done']),
                    ('l10n_be_short_signature', '!=', False)
                ])
                data = self._set_default_belgian_taxes_if_empty(data, "taxes")
                data = self._set_default_belgian_taxes_if_empty(data, "refund_taxes")
                cash_payment_methods = session.payment_method_ids.filtered(lambda pm: pm.type == 'cash')
                if cash_payment_methods:
                    default_cash_payment_method_id = cash_payment_methods[0]
                    total_payment = sum(
                        orders.payment_ids.filtered(lambda p: p.payment_method_id == default_cash_payment_method_id).mapped('amount')
                    )
                    total_cash_end = total_payment + session.cash_register_balance_start
                else:
                    total_cash_end = 0
                negQuantities = session._get_l10n_be_neg_quantities(orders)
                negRefunds = next((d for d in negQuantities if d.get("negQuantityReason") == "REFUND"), {})
                negCorrections = next((d for d in negQuantities if d.get("negQuantityReason") == "CORRECTION"), {})
                negPriceChanges = next((d for d in negQuantities if d.get("negQuantityReason") == "PRICE_CHANGE"), {})
                report_data = {
                    "l10n_be_pos_blackbox": True,
                    "cashier_name": session.user_id.name,
                    "establishment_number": config.establishment_number,
                    "l10n_be_insz_or_bis_number": session.user_id.l10n_be_insz_or_bis_number,
                    "l10n_be_N_event_counter": session.l10n_be_N_event_counter,
                    "l10n_be_N_event_amount": session.l10n_be_N_event_amount,
                    "l10n_be_NR_event_counter": session.l10n_be_NR_event_counter,
                    "l10n_be_NR_event_amount": session.l10n_be_NR_event_amount,
                    "l10n_be_P_event_counter": session.l10n_be_P_event_counter,
                    "l10n_be_P_event_amount": session.l10n_be_P_event_amount,
                    "l10n_be_I_event_counter": session.l10n_be_I_event_counter,
                    "l10n_be_I_event_amount": session.l10n_be_I_event_amount,
                    "l10n_be_T_event_counter": session.l10n_be_T_event_counter,
                    "l10n_be_T_event_amount": session.l10n_be_T_event_amount,
                    "l10n_be_sign_drawer_open_amount": session.l10n_be_sign_drawer_open_amount,
                    "CashBoxStartAmount": session.cash_register_balance_start,
                    "CashBoxEndAmount": total_cash_end,
                    "cashRegisterID": config.name,
                    "fdmID": config.l10n_be_blackbox_be_id.name,
                    "posID": config.l10n_be_pos_id,
                    "bookingPeriodId": session.name,
                    "bookingDate": session.start_at,
                    "firstFdmRef": session.first_fdm_ref,
                    "lastFdmRef": session.last_fdm_ref,
                    "posDevices": session._get_l10n_be_pos_devices(orders),
                    "fdmDevices": session._get_l10n_be_fdm_devices(orders),
                    "turnoverTransactions": session._get_l10n_be_turnover_transactions(),
                    "departments": session._get_l10n_be_departments(data["products"], data["refund_products"]),
                    "negQuantities": negQuantities,
                    "negRefunds": negRefunds,
                    "negCorrections": negCorrections,
                    "negPriceChanges": negPriceChanges,
                    "l10_be_payments": session._get_l10n_be_payments(data['payments_per_method']),
                    "vats": session._get_l10n_be_vats(data["taxes"], data["refund_taxes"]),
                    "drawersOpenCount": len(session.statement_line_ids),
                    "priceChanges": session._get_l10n_be_price_changes(orders),
                    "l10_be_invoices": session._get_l10n_be_invoices(data['invoiceList'][0]['invoices']),
                    "l10n_be_turnover_z_report_fdm_ref": session.l10n_be_turnover_z_report_fdm_ref,
                }
                if session.state == "closed" or before_closing:
                    report_data["reportBookingDate"] = (session.stop_at or fields.Datetime.now()).date().isoformat()
                    report_data["reportNo"] = config.l10n_be_report_counter
                data.update(report_data)

        data["total_paid"] = totalPaymentsAmount
        return data

    @api.model
    def _get_report_values(self, docids, data=None):
        if (docids and len(docids) == 1) or (data and data.get('session_ids') and len(data['session_ids']) == 1):
            session = self.env['pos.session'].browse(docids) if len(docids) == 1 else self.env['pos.session'].browse(data['session_ids'][0])
            if session.exists() and session.config_id.l10n_be_blackbox_be_id and not data['context'].get('called_from_pos') and not self.env.context.get('skip_sale_details_compute'):
                # Only authorize report generation from the POS (because we need to 'signReport' to the Belgian Blackbox )
                raise UserError(_("You cannot print the Sale details report for a POS session with a Belgian Blackbox configured from the backend. Please print it from the POS interface instead.\nYou can also download Z report from the chatter of closed sessions."))
        if self.env.context.get('skip_sale_details_compute'):
            return data
        return super()._get_report_values(docids, data=data)

    def _get_product_total_amount(self, line):
        return line.price_subtotal_incl

    def _get_total_and_qty_per_category(self, categories):
        res_cat, res_total = super()._get_total_and_qty_per_category(categories)
        config_id = self.env.context.get('config_id')
        if config_id and self.env['pos.config'].browse(config_id).l10n_be_blackbox_be_id:
            for cat in res_cat:
                total_cat = 0
                for product in cat['products']:
                    total_cat += product['total_paid']
                cat['total'] = total_cat
            unique_products = list({tuple(sorted(product.items())): product for category in categories for product in category['products']}.values())
            res_total['total'] = sum(product['total_paid'] for product in unique_products)
        return res_cat, res_total

    def _set_default_belgian_taxes_if_empty(self, data, taxes_name):
        for tax in data[taxes_name]:
            tax_used = self.env['account.tax'].search([('name', '=', tax['name'])])
            tax['identification_letter'] = tax_used.tax_group_id.pos_receipt_label or 'D'
            tax['rate'] = tax_used.amount

        letter_set = ['A', 'B', 'C', 'D']
        for tax in data[taxes_name]:
            if tax['identification_letter'] in letter_set:
                letter_set.remove(tax['identification_letter'])

        for letter in letter_set:
            if letter == 'A':
                data[taxes_name].append({
                    'name': '21%',
                    'tax_amount': 0.0,
                    'base_amount': 0.0,
                    'identification_letter': letter,
                    'rate': 21.0
                })
            if letter == 'B':
                data[taxes_name].append({
                    'name': '12%',
                    'tax_amount': 0.0,
                    'base_amount': 0.0,
                    'identification_letter': letter,
                    'rate': 12.0
                })
            if letter == 'C':
                data[taxes_name].append({
                    'name': '6%',
                    'tax_amount': 0.0,
                    'base_amount': 0.0,
                    'identification_letter': letter,
                    'rate': 6.0
                })
            if letter == 'D':
                data[taxes_name].append({
                    'name': '0%',
                    'tax_amount': 0.0,
                    'base_amount': 0.0,
                    'identification_letter': letter,
                    'rate': 0.0
                })
        data[taxes_name] = sorted(data[taxes_name], key=lambda d: d['identification_letter'], reverse=True)

        return data
