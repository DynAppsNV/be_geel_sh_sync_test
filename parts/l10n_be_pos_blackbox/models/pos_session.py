from odoo import models, fields, api, Command
from collections import defaultdict
from itertools import groupby
import base64
import uuid
import pytz


class PosSession(models.Model):
    _inherit = "pos.session"

    l10n_be_users_clocked_ids = fields.Many2many(
        "res.users",
        "users_session_clocking_info",
        string="Clocked In Users",
    )
    pos_clock_in_out_ids = fields.One2many('pos.clock.in.out', 'session_id', string='POS Clock In/Out')

    l10n_be_N_event_counter = fields.Integer()
    l10n_be_N_event_amount = fields.Monetary()
    l10n_be_NR_event_counter = fields.Integer()
    l10n_be_NR_event_amount = fields.Monetary()
    l10n_be_P_event_counter = fields.Integer()
    l10n_be_P_event_amount = fields.Monetary()
    l10n_be_I_event_counter = fields.Integer()
    l10n_be_I_event_amount = fields.Monetary()
    l10n_be_T_event_counter = fields.Integer()
    l10n_be_T_event_amount = fields.Monetary()

    l10n_be_sign_drawer_open_amount = fields.Integer()

    l10n_be_correction_qty_count = fields.Integer()
    l10n_be_correction_ticket_count = fields.Integer()
    l10n_be_correction_amount = fields.Monetary()
    l10n_be_price_change_qty_count = fields.Integer()
    l10n_be_price_change_ticket_count = fields.Integer()
    l10n_be_price_change_amount = fields.Monetary()

    l10n_be_turnover_z_report_fdm_ref = fields.Json(string="Turnover Z Report FDM Reference")
    l10n_be_user_z_report_fdm_ref = fields.Json(string="User Z Report FDM Reference")

    booking_period_id = fields.Char(string='Booking Period ID', default=lambda self: str(uuid.uuid4()), readonly=True, copy=False)

    first_fdm_ref = fields.Json(string="First FDM Reference", readonly=True, copy=False)
    last_fdm_ref = fields.Json(string="Last FDM Reference", readonly=True, copy=False)

    old_pos_blackbox_be_data = fields.Json(string="Old POS Blackbox BE Data", readonly=True, copy=False)

    @api.model
    def _load_pos_data_models(self, config_id):
        return super()._load_pos_data_models(config_id) + ['pos.blackbox.be', 'ir.ui.view']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['l10n_be_users_clocked_ids', 'booking_period_id']

    def is_session_closable(self, bank_payment_method_diffs=None):
        self.ensure_one()
        result = self._cannot_close_session(dict(bank_payment_method_diffs or []))
        return not bool(result)

    def set_work_in_out_cashier(self, cashier_id, action="in"):
        self.ensure_one()
        cashier = self.env['res.users'].browse(cashier_id)
        clocked_ids = self.l10n_be_users_clocked_ids

        if action == 'in' and cashier not in clocked_ids:
            self.l10n_be_users_clocked_ids |= cashier
            self._create_clock_events(cashier, 'in')
        elif action == 'out' and cashier in clocked_ids:
            self.l10n_be_users_clocked_ids -= cashier
            self._create_clock_events(cashier, 'out')

    def work_out_all_cashiers(self):
        self.ensure_one()
        clocked_ids = self.l10n_be_users_clocked_ids
        self._create_clock_events(clocked_ids, 'out')
        self.l10n_be_users_clocked_ids = [Command.clear()]
        return clocked_ids.mapped('l10n_be_insz_or_bis_number')

    def increment_l10n_be_counters(self, event_label, amount):
        self.ensure_one()
        if event_label == "N":
            self.l10n_be_N_event_counter += 1
            self.l10n_be_N_event_amount += self.currency_id.round(amount)
            if amount < 0:
                self.l10n_be_NR_event_counter += 1
                self.l10n_be_NR_event_amount += self.currency_id.round(amount)
        elif event_label == "P":
            self.l10n_be_P_event_counter += 1
            self.l10n_be_P_event_amount += self.currency_id.round(amount)
        elif event_label == "I":
            self.l10n_be_I_event_counter += 1
            self.l10n_be_I_event_amount += self.currency_id.round(amount)
        elif event_label == "T":
            self.l10n_be_T_event_counter += 1
            self.l10n_be_T_event_amount += self.currency_id.round(amount)

    def handle_blackbox_signature(self, signatures_batch):
        """ Set the first and last FDM reference for the session based on the given blackbox signature. """
        self.ensure_one()
        for data in signatures_batch:
            blackbox_signature = data.get('signature')
            amount = data.get('amount', 0)
            is_self_session = data.get('isSelfSession')
            data = data.get('data', {})

            if blackbox_signature.get('fdmRef') is not None and blackbox_signature['fdmRef'].get('eventLabel') is not None:
                if is_self_session and blackbox_signature['fdmRef']['eventLabel'] not in ['R', 'C']:
                    if not self.first_fdm_ref:
                        self.first_fdm_ref = blackbox_signature['fdmRef']
                    self.last_fdm_ref = blackbox_signature['fdmRef']
                if blackbox_signature['eventOperation'] == 'REPORT_TURNOVER_Z':
                    self.l10n_be_turnover_z_report_fdm_ref = blackbox_signature['fdmRef']
                    self.config_id.l10n_be_report_counter += 1
                elif blackbox_signature['eventOperation'] == 'REPORT_USER_Z':
                    self.l10n_be_user_z_report_fdm_ref = blackbox_signature['fdmRef']
                    self.config_id.l10n_be_report_counter += 1
                elif blackbox_signature['eventOperation'] == 'DRAWER_OPEN':
                    self.l10n_be_sign_drawer_open_amount += 1

                if blackbox_signature['fdmRef']['eventLabel'] in ['N', 'P', 'I', 'T']:
                    self.increment_l10n_be_counters(
                        blackbox_signature['fdmRef']['eventLabel'],
                        amount,
                    )
                    # If it's a signOrder, we check if there was a negQuantityReason "CORRECTION", or "PRICE_CHANGE"
                    if blackbox_signature['eventOperation'] == 'ORDER':
                        transaction_lines = data.get('transaction', {}).get('transactionLines', [])
                        has_correction = False
                        has_price_change = False
                        correction_qty = 0
                        correction_amount = 0.0
                        price_change_qty = 0
                        price_change_amount = 0.0
                        for line in transaction_lines:
                            main_product = line.get('mainProduct', {})
                            neg_reason = main_product.get('negQuantityReason')
                            quantity = main_product.get('quantity', 0)
                            line_total = line.get('lineTotal', 0.0)
                            if neg_reason == 'CORRECTION':
                                has_correction = True
                                correction_qty += abs(quantity)
                                correction_amount += line_total
                            elif neg_reason == 'PRICE_CHANGE':
                                has_price_change = True
                                price_change_qty += abs(quantity)
                                price_change_amount += line_total

                        if has_correction:
                            self.l10n_be_correction_qty_count += correction_qty
                            self.l10n_be_correction_ticket_count += 1
                            self.l10n_be_correction_amount += correction_amount
                        if has_price_change:
                            self.l10n_be_price_change_qty_count += price_change_qty
                            self.l10n_be_price_change_ticket_count += 1
                            self.l10n_be_price_change_amount += price_change_amount

    def get_l10n_be_user_report_data(self, before_closing=False):
        """ Return all data used in the user report """
        self.ensure_one()
        orders = self.env["pos.order"].search([
            ("session_id", "=", self.id),
            ('state', 'in', ['paid', 'done']),
            ('l10n_be_short_signature', '!=', False)
        ])

        user_report_data = {
            'posDevices': self._get_l10n_be_pos_devices(orders),
            'fdmDevices': self._get_l10n_be_fdm_devices(orders),
            'users': self._get_l10n_be_users_data(orders),
        }
        if self.state == "closed" or before_closing:
            stop_at_dt = self.stop_at or fields.Datetime.now()
            user_report_data["reportBookingDate"] = stop_at_dt.date().isoformat()
            user_report_data["reportNo"] = self.config_id.l10n_be_report_counter
            user_report_data["l10n_be_user_z_report_fdm_ref"] = self.l10n_be_user_z_report_fdm_ref
            user_report_data["stop_at"] = stop_at_dt
        return user_report_data

    def generate_l10n_z_reports_attachments(self, sale_details_data, user_report_data):
        """ Generates both the Sale Details Z report and the User Z report and attaches them to the session """
        self.ensure_one()
        report_env = self.with_context(skip_sale_details_compute=True)

        sale_pdf, _ = report_env.env['ir.actions.report']._render_qweb_pdf(
            'point_of_sale.sale_details_report',
            data=sale_details_data,
        )
        sale_attachment_name = f'{self.name.replace(" ", "_")}_Sale_Details_Report_Z.pdf'

        sale_attach = self.env['ir.attachment'].create({
            'name': sale_attachment_name,
            'type': 'binary',
            'datas': base64.b64encode(sale_pdf),
            'res_model': 'pos.session',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        self.message_post(
            body="Sale Details Report Z has been generated.",
            attachment_ids=[sale_attach.id],
        )

        user_pdf, _ = report_env.env['ir.actions.report']._render_qweb_pdf(
            'l10n_be_pos_blackbox.user_report_template',
            [self.id],
            data=user_report_data,
        )
        user_attachment_name = f'{self.name.replace(" ", "_")}_Users_Report_Z.pdf'

        user_attach = self.env['ir.attachment'].create({
            'name': user_attachment_name,
            'type': 'binary',
            'datas': base64.b64encode(user_pdf),
            'res_model': 'pos.session',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        self.message_post(
            body="User Report Z has been generated.",
            attachment_ids=[user_attach.id],
        )

    def _create_clock_events(self, cashiers, action):
        self.ensure_one()
        if not cashiers:
            return

        vals_list = []
        for cashier in cashiers:
            vals = {
                'type': action,
                'session_id': self.id,
            }
            if self.config_id.module_pos_hr:
                vals['employee_id'] = cashier.id
            else:
                vals['user_id'] = cashier.id

            vals_list.append(vals)

        self.env['pos.clock.in.out'].create(vals_list)

    def _get_l10n_be_cashier_social_events(self, cashier_clock_events):
        """ Return the social events (clock in/out) of a cashier. """
        social_events = []
        for event in cashier_clock_events:
            social_events.append({
                'inOut': event.type.upper(),
                'posDateTime': self.rfc3339_datetime(event.event_date_time),
            })
        return social_events

    def _get_l10n_be_users_data(self, orders):
        """ Return summarized users (cashiers) information from the given orders. """
        users = []
        # itertools.groupby() only groups consecutive elements with the same key.
        orders = orders.sorted(lambda order: order._get_cashier().id)
        for cashier, group in groupby(orders, lambda order: order._get_cashier()):
            insz = cashier.sudo().l10n_be_insz_or_bis_number or cashier.sudo().employee_id.l10n_be_insz_or_bis_number
            cashier_clock_events = cashier.pos_clock_in_out_ids.filtered(lambda e: e.session_id == self)
            group_orders = list(group)

            if cashier_clock_events:
                first_pos_dt = min(cashier_clock_events.mapped('event_date_time'))
                last_pos_dt = max(cashier_clock_events.mapped('event_date_time'))
            else:
                # FIXME: this is a temporary fallback for mobile orders without clock events
                # TODO-manv: FW-19.1: directly contact OBOX via backend to sign mobile orders
                # We will also first ensure that the cashier is clocked in (for self-ordering), so we should always have clock events for the cashier
                first_pos_dt = min(order.date_order for order in group_orders)
                last_pos_dt = max(order.date_order for order in group_orders)

            cashier_data = {
                'employeeId': insz,
                'totalAmount': 0,
                'socialEvents': self._get_l10n_be_cashier_social_events(cashier_clock_events),
                'firstPosDateTime': self.rfc3339_datetime(first_pos_dt),
                'lastPosDateTime': self.rfc3339_datetime(last_pos_dt),
                # Leading '_' keeps this field for reports only; it's filtered out before sending to the blackbox in js side (see 'extractFdmData()').
                '_name': cashier.name,
            }
            cashier_payments = {}
            for order in group_orders:
                cashier_data['totalAmount'] = self.currency_id.round(cashier_data['totalAmount'] + order.amount_paid)
                for payment in order.payment_ids:
                    pm_id = str(payment.payment_method_id.id)
                    pm_entry = cashier_payments.get(pm_id)
                    if pm_entry:
                        cashier_payments[pm_id]['amount']['normalAmount'] = self.currency_id.round(cashier_payments[pm_id]['amount']['normalAmount'] + payment.amount)
                        cashier_payments[pm_id]['amount']['totalAmount'] = self.currency_id.round(cashier_payments[pm_id]['amount']['totalAmount'] + payment.amount)
                    else:
                        cashier_payments[pm_id] = {
                            'id': pm_id,
                            'name': payment.payment_method_id.name,
                            'type': payment.payment_method_id._get_mapped_payment_type(),
                            'amount': {
                                'type': "PAYMENT",
                                'totalAmount': self.currency_id.round(payment.amount),
                                'normalAmount': self.currency_id.round(payment.amount),
                                'negativeCorrections': 0,
                                'positiveCorrections': 0,
                                'correctionsCount': 0,
                            }
                        }
            cashier_data['payments'] = list(cashier_payments.values())
            users.append(cashier_data)
        return users

    def _get_l10n_be_invoices(self, data_invoices):
        """Return summarized invoices information from the given data invoices."""
        invoices = []
        for invoice in data_invoices:
            invoices.append({
                "invoiceNo": f"invoice-{invoice.get('id')}",
                "amount": invoice.get("total"),
            })
        return invoices

    def _get_l10n_be_payments(self, data_payments):
        """Return summarized payments information from the given data payments."""
        payments = []
        for payment in data_payments:
            pm = self.env['pos.payment.method'].browse(payment.get("id"))
            payments.append({
                "id": str(payment.get("id")),
                "name": payment.get("name"),
                "type": pm._get_mapped_payment_type(),
                "amount": {
                    "type": "PAYMENT",
                    "totalAmount": payment.get("total"),
                    "normalAmount": payment.get("total"),
                    "negativeCorrections": 0,
                    "positiveCorrections": 0,
                    "correctionsCount": 0,
                }
            })
        return payments

    def _get_l10n_be_vats(self, data_taxes, data_refund_taxes):
        """Return summarized VAT information from the given data taxes and refund taxes."""
        vats = defaultdict(lambda: {
            "taxableAmount": 0,
            "vatAmount": 0,
            "totalAmount": 0,
            "rate": 0,
            "label": ""
        })

        for tax in (*data_taxes, *data_refund_taxes):
            label = tax.get("identification_letter")
            base, tax_amount = tax.get("base_amount", 0), tax.get("tax_amount", 0)
            total = base + tax_amount
            vat = vats[label]
            vat.update(label=label, rate=tax.get("rate"))
            vat["taxableAmount"] += base
            vat["vatAmount"] += tax_amount
            vat["totalAmount"] += total

        for vat in vats.values():
            vat["taxableAmount"] = self.currency_id.round(vat["taxableAmount"])
            vat["vatAmount"] = self.currency_id.round(vat["vatAmount"])
            vat["totalAmount"] = self.currency_id.round(vat["totalAmount"])
        return list(vats.values())

    def _get_l10n_be_pos_devices(self, orders):
        """Return summarized POS devices information from the given orders.

        Each entry groups orders by (posId, terminalId) and provides:
        - posId: the POS ID (l10n_be_pos_id)
        - terminalId: the terminal ID (l10n_be_terminal_id)
        - firstPosDateTime: earliest l10n_be_pos_date_time
        - lastPosDateTime: latest l10n_be_pos_date_time
        """
        pos_devices_map = defaultdict(list)

        for order in orders:
            pos_id = order.l10n_be_pos_id
            terminal_id = order.l10n_be_terminal_id
            if not pos_id or not terminal_id:
                continue
            pos_devices_map[pos_id, terminal_id].append(order.l10n_be_pos_date_time)

        pos_devices = []
        for (pos_id, terminal_id), date_list in pos_devices_map.items():
            first_dt = min(date_list)
            last_dt = max(date_list)

            pos_devices.append({
                "posId": pos_id,
                "terminalId": terminal_id,
                "firstPosDateTime": self.rfc3339_datetime(first_dt),
                "lastPosDateTime": self.rfc3339_datetime(last_dt),
            })

        return pos_devices

    def _get_l10n_be_fdm_devices(self, orders):
        """Return summarized FDM device information from the given orders.

        Each entry groups orders by FDM ID and provides:
        - fdmId: the FDM ID (l10n_be_fdm_id)
        - firstFdmDateTime: earliest l10n_be_fdm_date_time
        - firstTotalCounter: total counter at that first FDM datetime
        - lastFdmDateTime: latest l10n_be_fdm_date_time
        - lastTotalCounter: total counter at that last FDM datetime
        """
        fdm_map = defaultdict(list)

        for order in orders:
            fdm_id = order.l10n_be_fdm_id
            if not fdm_id:
                continue
            fdm_map[fdm_id].append(order)

        fdm_devices = []
        for fdm_id, fdm_orders in fdm_map.items():
            fdm_orders.sort(key=lambda o: o.l10n_be_fdm_date_time)

            first_order = fdm_orders[0]
            last_order = fdm_orders[-1]

            fdm_devices.append({
                "fdmId": fdm_id,
                "firstFdmDateTime": self.rfc3339_datetime_utc(first_order.l10n_be_fdm_date_time),
                "firstTotalCounter": first_order.l10n_be_total_counter,
                "lastFdmDateTime": self.rfc3339_datetime_utc(last_order.l10n_be_fdm_date_time),
                "lastTotalCounter": last_order.l10n_be_total_counter,
            })

        return fdm_devices

    def _get_l10n_be_departments(self, product_data, refund_product_data):
        """Return summarized departments (category) information from the given product data. """
        departments = []

        def add_department_id(products):
            for dept in products:
                first_dep_product = self.env["product.product"].browse(dept['products'][0]['product_id'])
                is_dep = first_dep_product and first_dep_product.pos_categ_ids
                dep_id = first_dep_product.pos_categ_ids[0].id if is_dep else 0
                dept['id'] = dep_id
        add_department_id(product_data)
        add_department_id(refund_product_data)

        merged_products = defaultdict(dict)
        # Start with product_data as positive
        for row in product_data:
            rid = row["id"]
            if not merged_products[rid]:
                merged_products[rid]["id"] = rid
                merged_products[rid]["name"] = row.get("name")
            merged_products[rid]["total"] = merged_products[rid].get("total", 0) + row.get("total", 0)

        # Subtract refund_product_data
        for row in refund_product_data:
            rid = row["id"]
            if not merged_products[rid]:
                merged_products[rid]["id"] = rid
                merged_products[rid]["name"] = row.get("name")
            merged_products[rid]["total"] = merged_products[rid].get("total", 0) - row.get("total", 0)

        merged_products = list(merged_products.values())

        for dept in merged_products:
            departments.append({
                "departmentId": str(dept["id"]),
                "departmentName": dept.get("name"),
                "amount": self.currency_id.round(dept.get("total")),
            })

        return departments

    def _get_l10n_be_turnover_transactions(self):
        """Return turnover transactions summary for the session."""
        return [
            {
                "eventLabel": "N",
                "ticketCount": self.l10n_be_N_event_counter,
                "amount": self.l10n_be_N_event_amount,
            },
            {
                "eventLabel": "P",
                "ticketCount": self.l10n_be_P_event_counter,
                "amount": self.l10n_be_P_event_amount,
            },
            {
                "eventLabel": "I",
                "ticketCount": self.l10n_be_I_event_counter,
                "amount": self.l10n_be_I_event_amount,
            },
            {
                "eventLabel": "T",
                "ticketCount": self.l10n_be_T_event_counter,
                "amount": self.l10n_be_T_event_amount,
            }
        ]

    def _get_l10n_be_neg_quantities(self, orders):
        """ Return negative quantities summary from the given orders. """
        res = []
        refund_orders = orders.filtered(lambda o: o.is_refund)
        if refund_orders:
            res.append({
                "negQuantityReason": "REFUND",
                "ticketCount": len(refund_orders),
                "negQuantityCount": len(refund_orders.mapped('lines')),
                "amount": sum(refund_orders.mapped('amount_paid')),
            })
        if self.l10n_be_correction_ticket_count:
            res.append({
                "negQuantityReason": "CORRECTION",
                "ticketCount": self.l10n_be_correction_ticket_count,
                "negQuantityCount": self.l10n_be_correction_qty_count,
                "amount": self.currency_id.round(self.l10n_be_correction_amount),
            })
        if self.l10n_be_price_change_ticket_count:
            res.append({
                "negQuantityReason": "PRICE_CHANGE",
                "ticketCount": self.l10n_be_price_change_ticket_count,
                "negQuantityCount": self.l10n_be_price_change_qty_count,
                "amount": self.currency_id.round(self.l10n_be_price_change_amount),
            })
        return res

    def _get_l10n_be_price_changes(self, orders):
        """Return summarized PUBLIC price changes from given orders."""
        price_changes = []
        vats = orders.lines.mapped('l10n_be_vats')

        totals = defaultdict(lambda: {'negative': 0.0, 'positive': 0.0})

        for vat_list in vats:
            if not vat_list:
                continue
            for vat in vat_list:
                label = vat.get('label')
                for change in vat.get('priceChanges', []):
                    if change.get('type') != 'PUBLIC':
                        continue
                    key = (change['id'], change['name'], change['type'], label)
                    amount = change.get('amount', 0.0)
                    if amount < 0:
                        totals[key]['negative'] += amount
                    elif amount > 0:
                        totals[key]['positive'] += amount

        grouped = defaultdict(list)
        for (cid, name, ctype, label), vals in totals.items():
            grouped[cid, name, ctype].append({
                'label': label,
                'negative': round(vals['negative'], 2),
                'positive': round(vals['positive'], 2),
            })

        for (cid, name, ctype), amounts in grouped.items():
            price_changes.append({
                'id': str(cid),
                'name': name,
                'type': ctype,
                'amount': amounts,
            })

        return price_changes

    def rfc3339_datetime(self, dt):
        """
        Convert a datetime object to an RFC 3339 formatted string.
        This is the required format to communicate POS date time
        Example:
            >>> rfc3339_datetime(datetime(2024, 6, 1, 12, 0, 0))
            '2024-06-01T12:00:00.000+02:00'
        """
        brussels = pytz.timezone("Europe/Brussels")
        local_dt = brussels.localize(dt) if dt.tzinfo is None else dt.astimezone(brussels)
        return local_dt.isoformat(timespec='milliseconds')

    def rfc3339_datetime_utc(self, dt):
        """
        Convert a datetime to an RFC 3339 UTC datetime formatted string.
        This is the required format to communicate FDM date time
        Example:
            >>> rfc3339_datetime_utc(datetime(2024, 6, 1, 12, 0, 0))
            '2024-06-01T10:00:00.000Z'
        """
        brussels = pytz.timezone("Europe/Brussels")
        local_dt = brussels.localize(dt) if dt.tzinfo is None else dt.astimezone(brussels)
        utc_dt = local_dt.astimezone(pytz.UTC)
        return utc_dt.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
