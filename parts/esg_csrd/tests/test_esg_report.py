from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestEsgReport(TransactionCase):
    def test_esg_report_base_year_validation(self):
        """Test that the base year validation works correctly."""
        EsgReport = self.env['esg.report']
        # Test with a valid base year
        report = EsgReport.create({
            'title': 'Test Report',
            'report_type': 'vsme_basic',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'base_year': 2024,
        })
        self.assertEqual(report.base_year, 2024)

        # Test with an invalid base year
        with self.assertRaises(ValidationError):
            EsgReport.create({
                'title': 'Invalid Report',
                'report_type': 'vsme_basic',
                'start_date': '2026-01-01',
                'end_date': '2026-12-31',
                'base_year': 10,
            })
