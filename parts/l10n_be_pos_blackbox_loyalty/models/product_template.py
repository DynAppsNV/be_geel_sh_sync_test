from odoo import api, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.constrains('taxes_id')
    def _ensure_gift_card_ewallet_product_no_taxes(self):
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
                # Programs enabled on this POS config
                gift_card_programs = config._get_program_ids().filtered(
                    lambda p: p.company_id == config.company_id and p.program_type == 'gift_card' and bool(p.trigger_product_ids & variants)
                )
                if gift_card_programs:
                    raise UserError(
                        _(
                            "Gift card products used in loyalty programs must not have any taxes when used with a certified blackbox.\n"
                            "Please remove taxes from the gift card product: %s",
                            product.display_name
                        )
                    )
                ewallet_programs = config._get_program_ids().filtered(
                    lambda p: p.company_id == config.company_id and p.program_type == 'ewallet' and bool(p.trigger_product_ids & variants)
                )
                if ewallet_programs:
                    raise UserError(
                        _(
                            "EWallet products used in loyalty programs must not have any taxes when used with a certified blackbox.\n"
                            "Please remove taxes from the eWallet product: %s",
                            product.display_name
                        )
                    )
