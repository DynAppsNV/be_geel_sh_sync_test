from odoo import api, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.constrains('taxes_id')
    def _check_settle_product_taxes(self):
        for product in self:
            belgian_taxes = product.taxes_id.filtered(
                lambda t: t.company_id.country_id.code == 'BE'
            )
            if not belgian_taxes:
                continue
            variants = product.product_variant_ids
            pos_configs = self.env['pos.config'].search([
                ('l10n_be_blackbox_be_id', '!=', False),
                ('company_id.chart_template', '=', 'be_comp')
            ])
            for config in pos_configs:
                # Settle products enabled on this POS config
                settle_products = config.settle_due_product_id | config.deposit_product_id | config.settle_invoice_product_id
                if variants & settle_products:
                    raise UserError(
                        _(
                            "Products used for settling due amounts, deposits, or invoice settlements in POS with a certified Belgian blackbox must not have any taxes.\n"
                            "Please remove all taxes from the product: %s",
                            product.display_name
                        )
                    )
