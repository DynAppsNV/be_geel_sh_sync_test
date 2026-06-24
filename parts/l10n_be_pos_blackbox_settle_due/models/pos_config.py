from odoo import models, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _check_l10n_be_before_opening(self):
        super()._check_l10n_be_before_opening()
        for config in self.filtered('l10n_be_blackbox_be_id'):
            config._check_settle_product_taxes()

    def _check_settle_product_taxes(self):
        for config in self:
            if config.l10n_be_blackbox_be_id:
                settle_products = config.settle_due_product_id | config.deposit_product_id | config.settle_invoice_product_id
                settle_products_be_taxes = settle_products.taxes_id.filtered(
                    lambda t: t.company_id.country_id.code == 'BE'
                )
                if settle_products_be_taxes:
                    product_names = ", ".join(settle_products_be_taxes.mapped("display_name"))
                    raise UserError(
                        _(
                            "Products used for settling due amounts, deposits, or invoice settlements in POS with a certified Belgian blackbox must not have any taxes.\n"
                            "Please remove taxes from the following products: %s",
                            product_names
                        )
                    )
