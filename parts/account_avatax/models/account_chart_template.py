from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _get_avatax_fiscal_position(self, country_code):
        return {
            f'account_fiscal_position_avatax_{country_code}': {
                'name': 'Automatic Tax Mapping (AvaTax)',
                'is_avatax': True,
                'auto_apply': False,
                'country_id': self.env.ref(f'base.{country_code}').id,
                'sequence': 100,
            },
        }

    @template('us', 'account.fiscal.position')
    def _get_us_avatax_fiscal_position(self):
        return self._get_avatax_fiscal_position('us')

    @template('ca_2023', 'account.fiscal.position')
    def _get_ca_avatax_fiscal_position(self):
        return self._get_avatax_fiscal_position('ca')
