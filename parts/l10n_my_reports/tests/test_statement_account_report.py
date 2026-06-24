# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestStatementAccountReport(TransactionCase):

    def test_report_generation_with_and_without_domain(self):
        """Test that the statement account report can be generated with and without a domain"""
        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        report = self.env.ref('l10n_my_reports.action_report_statement_account')
        result = report._render_qweb_pdf(report.id, partner.ids, data={
            'date_to': '2024-01-01',
            'domain': [('date', '<=', '2024-01-01')],
        })
        self.assertTrue(result, "Report should generate with domain")
        result = report._render_qweb_pdf(report.id, partner.ids, data={
            'date_to': '2024-01-01',
        })
        self.assertTrue(result, "Report should generate without domain")
