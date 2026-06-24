from odoo import models


class L10nPtReportsEcSalesReportHandler(models.AbstractModel):
    _name = 'l10n_pt_reports.ec.sales.report.handler'
    _inherit = ['account.ec.sales.report.handler']
    _description = "Portuguese EC Sales Report Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options):
        """
        Add the invoice lines search domain that is specific to the country.
        Typically, the taxes account.report.expression ids relative to the country for the triangular, sale of goods
        or services.
        :param dict options: Report options
        :return dict: The modified options dictionary
        """
        super()._init_core_custom_options(report, options, previous_options)
        ec_operation_category = options.setdefault('sales_report_taxes', {})
        ec_operation_category.update(self._get_tax_tags_for_pt_sales_report())
        # Change the names of the taxes to specific ones that are dependant to the tax type
        ec_operation_category['operation_category'] = {
            'goods': 'ES',
            'triangular': 'ESSP',
            'services': 'ESSS',
        }

        options.update({'sales_report_taxes': ec_operation_category})

    def _get_tax_tags_for_pt_sales_report(self):
        return {
            'goods': tuple(self.env.ref('l10n_pt.trp_base_7_tag')._get_matching_tags().ids),
            'triangular': tuple(),
            'services': tuple(),
        }
