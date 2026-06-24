from freezegun import freeze_time

from odoo import Command
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nVnTaxReport(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('vn')
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_a.write({
            'country_id': cls.env.ref('base.vn').id,
            'vat': '0123456789',
        })
        cls.partner_b.write({
            'country_id': cls.env.ref('base.vn').id,
            'vat': '9876543210',
        })

        cls.sales_report = cls.env.ref('l10n_vn_reports.sales_tax_report')
        cls.purchase_report = cls.env.ref('l10n_vn_reports.purchase_tax_report')

        company_id = cls.company_data['company'].id
        cls.tax_sale_10 = cls.env.ref(f'account.{company_id}_tax_sale_vat10')
        cls.tax_sale_5 = cls.env.ref(f'account.{company_id}_tax_sale_vat5')
        cls.tax_purchase_10 = cls.env.ref(f'account.{company_id}_tax_purchase_vat10')
        cls.tax_purchase_5 = cls.env.ref(f'account.{company_id}_tax_purchase_vat5')

    @freeze_time('2024-06-30')
    def test_sales_tax_report(self):
        """ Test that the sales tax report correctly generates and aggregates invoice data. """
        # Create invoices with different tax rates
        self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2024-06-15',
                'invoice_line_ids': [
                    Command.create({
                        'name': 'Product A',
                        'quantity': 1,
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(self.tax_sale_10.ids)],
                    }),
                ],
            },
            {
                'move_type': 'out_invoice',
                'partner_id': self.partner_b.id,
                'invoice_date': '2024-06-20',
                'invoice_line_ids': [
                    Command.create({
                        'name': 'Product B',
                        'quantity': 1,
                        'price_unit': 500.0,
                        'tax_ids': [Command.set(self.tax_sale_5.ids)],
                    }),
                ],
            },
        ]).action_post()

        options = self._generate_options(self.sales_report, '2024-06-01', '2024-06-30', {'unfold_all': True})

        self.assertLinesValues(
            self.sales_report._get_lines(options),
            #   Name,                                            Invoice Number, Invoice Date,    Customer,       Tax ID,   Description, Untaxed Amount,  VAT Amount
            [      0,                                                         1,            2,           3,            4,             5,              6,          7],
            [
             ('June 2024',                                                   '',           '',          '',           '',            '',             '',         ''),
                 ('VAT on sales of goods and services 0%',                   '',           '',          '',           '',            '',             '',         ''),
                     ('Total VAT on sales of goods and services 0%',         '',           '',          '',           '',            '',             '',         ''),
                 ('VAT on sales of goods and services 5%',                   '',           '',          '',           '',            '',          500.0,       25.0),
                     ('INV/2024/00002',                                      '', '06/20/2024', 'partner_b', '9876543210',            '',          500.0,       25.0),
                         ('Value Added Tax (VAT) 5%',                        '',           '',          '',           '',            '',         -500.0,       25.0),
                     ('Total INV/2024/00002',                                '', '06/20/2024', 'partner_b', '9876543210',            '',          500.0,       25.0),
                 ('Total VAT on sales of goods and services 5%',             '',           '',          '',           '',            '',          500.0,       25.0),
                 ('VAT on sales of goods and services 8%',                   '',           '',          '',           '',            '',             '',         ''),
                     ('Total VAT on sales of goods and services 8%',         '',           '',          '',           '',            '',             '',         ''),
                 ('VAT on sales of goods and services 10%',                  '',           '',          '',           '',            '',         1000.0,      100.0),
                     ('INV/2024/00001',                                      '', '06/15/2024', 'partner_a', '0123456789',            '',         1000.0,      100.0),
                         ('Value Added Tax (VAT) 10%',                       '',           '',          '',           '',            '',        -1000.0,      100.0),
                     ('Total INV/2024/00001',                                '', '06/15/2024', 'partner_a', '0123456789',            '',         1000.0,      100.0),
                 ('Total VAT on sales of goods and services 10%',            '',           '',          '',           '',            '',         1000.0,      100.0),
                 ('VAT Exemption on sales of goods and services',            '',           '',          '',           '',            '',             '',         ''),
                     ('Total VAT Exemption on sales of goods and services',  '',           '',          '',           '',            '',             '',         ''),
                 ('Grand Total',                                             '',           '',          '',           '',            '',         1500.0,      125.0),
            ],
            options,
        )

    @freeze_time('2024-06-30')
    def test_purchase_tax_report(self):
        """ Test that the purchase tax report correctly generates and aggregates vendor bill data. """
        # Create vendor bills with different tax rates
        self.env['account.move'].create([
            {
                'move_type': 'in_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2024-06-15',
                'invoice_line_ids': [
                    Command.create({
                        'name': 'Service A',
                        'quantity': 2,
                        'price_unit': 500.0,
                        'tax_ids': [Command.set(self.tax_purchase_10.ids)],
                    }),
                ],
            },
            {
                'move_type': 'in_invoice',
                'partner_id': self.partner_b.id,
                'invoice_date': '2024-06-20',
                'invoice_line_ids': [
                    Command.create({
                        'name': 'Service B',
                        'quantity': 1,
                        'price_unit': 300.0,
                        'tax_ids': [Command.set(self.tax_purchase_5.ids)],
                    }),
                ],
            },
        ]).action_post()

        options = self._generate_options(self.purchase_report, '2024-06-01', '2024-06-30', {'unfold_all': True})

        self.assertLinesValues(
            self.purchase_report._get_lines(options),
            #   Name,                                                Invoice Number, Invoice Date,    Customer,       Tax ID,   Description, Untaxed Amount,  VAT Amount
            [      0,                                                             1,            2,           3,            4,             5,              6,          7],
            [
             ('June 2024',                                                       '',           '',          '',           '',            '',             '',         ''),
                 ('VAT on purchase of goods and services 0%',                    '',           '',          '',           '',            '',             '',         ''),
                     ('Total VAT on purchase of goods and services 0%',          '',           '',          '',           '',            '',             '',         ''),
                 ('VAT on purchase of goods and services 5%',                    '',           '',          '',           '',            '',          300.0,       15.0),
                     ('BILL/2024/06/0002',                                       '', '06/20/2024', 'partner_b', '9876543210',            '',          300.0,       15.0),
                         ('Deductible VAT 5%',                                   '',           '',          '',           '',            '',          300.0,       15.0),
                     ('Total BILL/2024/06/0002',                                 '', '06/20/2024', 'partner_b', '9876543210',            '',          300.0,       15.0),
                 ('Total VAT on purchase of goods and services 5%',              '',           '',          '',           '',            '',          300.0,       15.0),
                 ('VAT on purchase of goods and services 8%',                    '',           '',          '',           '',            '',             '',         ''),
                     ('Total VAT on purchase of goods and services 8%',          '',           '',          '',           '',            '',             '',         ''),
                 ('VAT on purchase of goods and services 10%',                   '',           '',          '',           '',            '',         1000.0,      100.0),
                     ('BILL/2024/06/0001',                                       '', '06/15/2024', 'partner_a', '0123456789',            '',         1000.0,      100.0),
                         ('Deductible VAT 10%',                                  '',           '',          '',           '',            '',         1000.0,      100.0),
                     ('Total BILL/2024/06/0001',                                 '', '06/15/2024', 'partner_a', '0123456789',            '',         1000.0,      100.0),
                 ('Total VAT on purchase of goods and services 10%',             '',           '',          '',           '',            '',         1000.0,      100.0),
                 ('VAT on Purchase of Goods and Services Tax Exempt',            '',           '',          '',           '',            '',             '',         ''),
                     ('Total VAT on Purchase of Goods and Services Tax Exempt',  '',           '',          '',           '',            '',             '',         ''),
                 ('Grand Total',                                                 '',           '',          '',           '',            '',         1300.0,      115.0),
            ],
            options,
        )
