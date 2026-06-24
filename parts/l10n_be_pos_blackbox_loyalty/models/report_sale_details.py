from odoo import models, api


class ReportPoint_Of_SaleReport_Saledetails(models.AbstractModel):
    _inherit = "report.point_of_sale.report_saledetails"

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        data = super().get_sale_details(
            date_start, date_stop, config_ids, session_ids, **kwargs
        )

        is_blackbox = False
        if config_ids:
            is_blackbox = bool(self.env['pos.config'].search([('id', 'in', config_ids), ('l10n_be_blackbox_be_id', '!=', False)], limit=1))
        elif session_ids:
            sessions = self.env['pos.session'].browse(session_ids)
            is_blackbox = any(s.config_id.l10n_be_blackbox_be_id for s in sessions)
        if not is_blackbox:
            return data

        data["payments_per_method"] = list(data.get("payments_per_method", []))
        total_ewallet = 0
        total_gift_card = 0
        dept_to_change = {}
        no_taxes = next((element for element in data["taxes"] if element.get("identification_letter") == "D"), None)

        for category in data['products']:
            filtered_products = []
            removed_total = 0.0
            removed_qty = 0.0

            for product in category.get("products", []):
                if product.get("is_gift_card") or product.get("is_ewallet"):
                    removed_total += product.get("total_paid", 0.0)
                    removed_qty += product.get("quantity", 0.0)
                    if product.get("is_gift_card"):
                        total_gift_card -= product.get("total_paid", 0.0)
                    if product.get("is_ewallet"):
                        total_ewallet -= product.get("total_paid", 0.0)
                else:
                    filtered_products.append(product)

            category["products"] = filtered_products
            if removed_qty > 0:
                category["total"] = category.get("total", 0.0) - removed_total
                dept_to_change[category["id"]] = {
                    "to_remove": removed_total,
                }
                category["qty"] = category.get("qty", 0.0) - removed_qty
                data["products_info"]["total"] = data["products_info"].get("total", 0.0) - removed_total
                data["products_info"]["qty"] = data["products_info"].get("qty", 0.0) - removed_qty
                if no_taxes:
                    no_taxes["base_amount"] -= removed_total
                    data["taxes_info"]["base_amount"] -= removed_total
                data["total_paid"] -= removed_total
                data["currency"]["total_paid"] -= removed_total

        for dept in data.get("departments", []):
            try:
                dept_id = int(dept["departmentId"])
            except (TypeError, ValueError):
                dept_id = None
            if dept_id is not None and dept_id in dept_to_change:
                dept["amount"] -= dept_to_change[dept_id]["to_remove"]

        if total_ewallet > 0:
            data["l10_be_payments"].append({
                "id": "ewallet",
                "name": "Ewallet",
                "type": "VOUCHER_OTHER",
                "amount": {
                    "type": "PAYMENT",
                    "totalAmount": total_ewallet,
                    "normalAmount": total_ewallet,
                    "negativeCorrections": 0,
                    "positiveCorrections": 0,
                    "correctionsCount": 0,
                }
            })
            data["payments"].append({
                'session': False,
                'name': 'Ewallet',
                'total': total_ewallet,
                'cash': False,
                'count': False,
            })
            data["payments_per_method"].append({
                'name': 'Ewallet',
                'total': total_ewallet,
            })
        if total_gift_card > 0:
            data["l10_be_payments"].append({
                "id": "gift_card",
                "name": "Gift Card",
                "type": "VOUCHER_STORE",
                "amount": {
                    "type": "PAYMENT",
                    "totalAmount": total_gift_card,
                    "normalAmount": total_gift_card,
                    "negativeCorrections": 0,
                    "positiveCorrections": 0,
                    "correctionsCount": 0,
                }
            })
            data["payments"].append({
                'session': False,
                'name': 'Gift Card',
                'total': total_gift_card,
                'cash': False,
                'count': False,
            })
            data["payments_per_method"].append({
                'name': 'Gift Card',
                'total': total_gift_card,
            })

        return data
