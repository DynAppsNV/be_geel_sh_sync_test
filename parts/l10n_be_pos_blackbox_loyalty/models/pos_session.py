from odoo import models
from collections import defaultdict


class PosSession(models.Model):
    _inherit = "pos.session"

    def _get_l10n_be_departments(self, product_data, refund_product_data):
        config_programs = self.env['loyalty.program'].search([
            ('program_type', 'in', ['gift_card', 'ewallet']),
            ('pos_config_ids', 'in', [False, self.config_id.id]),
        ])
        gift_card_products = config_programs.filtered_domain([
            ('program_type', 'in', ['gift_card']),
        ]).payment_program_discount_product_id._filtered_access('read')
        ewallet_products = config_programs.filtered_domain([
            ('program_type', 'in', ['ewallet']),
        ]).payment_program_discount_product_id._filtered_access('read')
        for dept in product_data:
            for product in dept['products']:
                if product['price_unit'] < 0 and product['product_id'] in gift_card_products.ids:
                    product['is_gift_card'] = True
                if product['price_unit'] < 0 and product['product_id'] in ewallet_products.ids:
                    product['is_ewallet'] = True

        departments = super()._get_l10n_be_departments(product_data, refund_product_data)
        return departments

    def _get_l10n_be_users_data(self, orders):
        users = super()._get_l10n_be_users_data(orders)
        loyalty_amounts = defaultdict(lambda: {"gift_card": 0.0, "ewallet": 0.0})

        users_by_employee_id = {
            user_data.get("employeeId"): user_data
            for user_data in users
            if user_data.get("employeeId")
        }

        for order in orders:
            cashier = order._get_cashier()
            employee_id = cashier.sudo().l10n_be_insz_or_bis_number
            if not employee_id:
                continue

            for line in order.lines:
                # Gift card / ewallet redemption lines are negative.
                if line.price_unit >= 0:
                    continue

                line_amount = abs(line.price_subtotal_incl)

                if line.reward_id.program_id.program_type == "gift_card":
                    loyalty_amounts[employee_id]["gift_card"] += line_amount
                elif line.reward_id.program_id.program_type == "ewallet":
                    loyalty_amounts[employee_id]["ewallet"] += line_amount

        def add_or_update_payment(user_data, payment_id, name, payment_type, amount):
            amount = self.currency_id.round(amount)
            if not amount:
                return

            for payment in user_data.get("payments", []):
                if payment.get("id") == payment_id:
                    payment["amount"]["normalAmount"] = self.currency_id.round(
                        payment["amount"]["normalAmount"] + amount
                    )
                    payment["amount"]["totalAmount"] = self.currency_id.round(
                        payment["amount"]["totalAmount"] + amount
                    )
                    return

            user_data.setdefault("payments", []).append({
                "id": payment_id,
                "name": name,
                "type": payment_type,
                "amount": {
                    "type": "PAYMENT",
                    "totalAmount": amount,
                    "normalAmount": amount,
                    "negativeCorrections": 0,
                    "positiveCorrections": 0,
                    "correctionsCount": 0,
                },
            })

        for employee_id, amounts in loyalty_amounts.items():
            user_data = users_by_employee_id.get(employee_id)
            if not user_data:
                continue

            add_or_update_payment(
                user_data,
                payment_id="gift_card",
                name="Gift Card",
                payment_type="VOUCHER_STORE",
                amount=amounts["gift_card"],
            )
            add_or_update_payment(
                user_data,
                payment_id="ewallet",
                name="Ewallet",
                payment_type="VOUCHER_OTHER",
                amount=amounts["ewallet"],
            )

        return users
