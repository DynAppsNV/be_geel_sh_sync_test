from odoo import api, models

SYNC_FIELDS = [
    "name",
    "active",
    "street",
    "street2",
    "zip",
    "city",
    "country_id",
    "lang",
    "currency_id",
    "vat",
    "email",
    "phone",
    "property_payment_term_id",
    "property_supplier_payment_term_id",
    "property_product_pricelist",
    "category_id",
    "user_id",
    "property_account_receivable_id",
    "property_inbound_payment_method_line_id",
    "buyer_id",
    "property_account_payable_id",
    "property_outbound_payment_method_line_id",
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _after_change_hook(self, method):
        for rec in self:
            PartnerModel = self.env["res.partner"].with_company(self.env.company).sudo()
            partner_company = PartnerModel.browse(rec.id)
            payment_term_client = partner_company.property_payment_term_id
            payment_term_supplier = partner_company.property_supplier_payment_term_id
            pricelist = partner_company.property_product_pricelist
            currency = pricelist.currency_id if pricelist else None

            payloads = []
            payload = {
                "Company_ID": None,
                "Contact_ID": rec.id,
                "Name_1": rec.name,
                "Name_2": "",
                "Preferred_Name": "",
                "Address": "",
                "Street_1": rec.street or "",
                "Street_2": rec.street2 or "",
                "Street_3": "",
                "Postal_Code": rec.zip or "",
                "City": rec.city or "",
                "Country": rec.country_id.id if rec.country_id else 0,
                "Language": rec.lang or "",
                "Currency": currency.id
                if currency
                else rec.currency_id.id
                if rec.currency_id
                else 0,
                "VAT_Prefix": "",
                "VAT_Number": rec.vat or "",
                "Email": rec.email or "",
                "Mobile": "",
                "Phone_1": rec.phone or "",
                "Phone_2": "",
                "Customer_Group": ",".join(rec.category_id.mapped("name")),
                "Sales_Representative": 0,
                "VAT_ID": "",
                "Journal": "",
                "General_Ledger": "",
                "Payment_Terms": 0,
                "Payment_Method": 0,
                "Blocked": not rec.active,
            }

            if not payment_term_client and not payment_term_supplier:
                payload.update({"Type": ""})
                payloads.append(payload.copy())
            else:
                if payment_term_client:
                    payload_client = payload.copy()
                    payment_method_id = partner_company.property_inbound_payment_method_line_id.id
                    payload_client.update(
                        {
                            "Type": "client",
                            "Company_ID": self.env.company.id,
                            "Sales_Representative": rec.user_id.id if rec.user_id else 0,
                            "General_Ledger": partner_company.property_account_receivable_id.code
                            if partner_company.property_account_receivable_id
                            else "",
                            "Payment_Terms": payment_term_client.id if payment_term_client else 0,
                            "Payment_Method": payment_method_id
                            if partner_company.property_inbound_payment_method_line_id
                            else 0,
                        }
                    )
                    payloads.append(payload_client)

                if payment_term_supplier:
                    payload_supplier = payload.copy()
                    payment_method_id = partner_company.property_outbound_payment_method_line_id.id
                    payload_supplier.update(
                        {
                            "Type": "supplier",
                            "Company_ID": self.env.company.id,
                            "Sales_Representative": rec.buyer_id.id if rec.buyer_id else 0,
                            "General_Ledger": partner_company.property_account_payable_id.code
                            if partner_company.property_account_payable_id
                            else "",
                            "Payment_Terms": payment_term_supplier.id
                            if payment_term_supplier
                            else 0,
                            "Payment_Method": payment_method_id
                            if partner_company.property_outbound_payment_method_line_id
                            else 0,
                        }
                    )
                    payloads.append(payload_supplier)

            endpoint = (
                self.env["ir.config_parameter"].sudo().get_param("xx_horizon.pas_contact_endpoint")
            )
            for payload in payloads:
                self.env["xx.sync.record"].queue(
                    env=self.env,
                    model=rec._name,
                    payload=payload,
                    endpoint=endpoint,
                    method=method,
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._after_change_hook("POST")
        return records

    def write(self, vals):
        res = super().write(vals)
        relevant_change = any(field in vals for field in SYNC_FIELDS)

        if relevant_change:
            self._after_change_hook("PUT")

        return res

    def unlink(self):
        self._after_change_hook("DELETE")
        return super().unlink()
