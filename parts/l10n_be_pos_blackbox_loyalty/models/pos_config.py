from odoo import models, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _check_l10n_be_before_opening(self):
        super()._check_l10n_be_before_opening()
        for config in self.filtered('l10n_be_blackbox_be_id'):
            config._check_loyalty()

    def _check_loyalty(self):
        for config in self:
            if config.l10n_be_blackbox_be_id:
                programs = config._get_program_ids().filtered(lambda p: p.company_id == config.company_id)
                gift_card_programs = programs.filtered(lambda p: p.program_type == 'gift_card')
                gift_card_be_taxes = gift_card_programs.trigger_product_ids.taxes_id.filtered(
                    lambda t: t.company_id.country_id.code == 'BE'
                )
                # We choose to only manage untaxed gift card products (see mutations UC260 & UC261) for simplicity
                if gift_card_be_taxes:
                    product_names = ", ".join(gift_card_be_taxes.mapped("display_name"))
                    raise UserError(
                        _(
                            "Gift card products used in loyalty programs must not have any taxes when used with a certified blackbox.\n"
                            "Please remove taxes from the following products: %s",
                            product_names
                        )
                    )
