# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon
from odoo.tests import tagged
from odoo.tools.misc import NON_BREAKING_SPACE
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class BelgiumSalesReportTest(AccountSalesReportCommon):

    @classmethod
    @AccountSalesReportCommon.setup_country('be')
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_b.update({
            'country_id': cls.env.ref('base.de').id,
            "vat": "DE123456788",
        })
        cls.company.update({
            'vat': 'BE0477472701',
        })
        cls.report = cls.env.ref('l10n_be_reports.belgian_ec_sales_report')

        cls.l_tax = cls.env['account.tax'].search([('name', '=', '0% EU M'), ('company_id', '=', cls.env.company.id)], limit=1)
        cls.t_tax = cls.env['account.tax'].search([('name', '=', '0% EU T'), ('company_id', '=', cls.env.company.id)], limit=1)
        cls.s_tax = cls.env['account.tax'].search([('name', '=', '0% EU S'), ('company_id', '=', cls.env.company.id)], limit=1)

    @freeze_time('2019-12-31')
    def test_ec_sales_report(self):
        self._create_invoices([
            (self.partner_a, self.l_tax, 300),
            (self.partner_a, self.l_tax, 300),
            (self.partner_a, self.t_tax, 500),
            (self.partner_b, self.t_tax, 500),
            (self.partner_a, self.s_tax, 700),
            (self.partner_b, self.s_tax, 700),
        ])

        options = self.report.get_options({'date': {'mode': 'range', 'filter': 'this_month'}})
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            # pylint: disable=C0326
            #   Partner                country code,            VAT Number,              Tax         Amount
            [   0,                     1,                       2,                       3,          4],
            [
                (self.partner_a.name,  self.partner_a.vat[:2],  self.partner_a.vat[2:],  'L (46L)',  f'600.00{NON_BREAKING_SPACE}€'),
                (self.partner_a.name,  self.partner_a.vat[:2],  self.partner_a.vat[2:],  'T (46T)',  f'500.00{NON_BREAKING_SPACE}€'),
                (self.partner_a.name,  self.partner_a.vat[:2],  self.partner_a.vat[2:],  'S (44)',   f'700.00{NON_BREAKING_SPACE}€'),
                (self.partner_b.name,  self.partner_b.vat[:2],  self.partner_b.vat[2:],  'T (46T)',  f'500.00{NON_BREAKING_SPACE}€'),
                (self.partner_b.name,  self.partner_b.vat[:2],  self.partner_b.vat[2:],  'S (44)',   f'700.00{NON_BREAKING_SPACE}€'),
                ('Total',              '',                      '',                      '',         f'3,000.00{NON_BREAKING_SPACE}€'),
            ],
            options,
        )

        expected_xml = '''
        <ns2:IntraConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/IntraConsignment" IntraListingsNbr="1">
            <ns2:IntraListing SequenceNumber="1" ClientsNbr="5" DeclarantReference="___ignore___" AmountSum="3000.00">
                <ns2:Declarant>
                    <VATNumber>0477472701</VATNumber>
                    <Name>company_1_data</Name>
                    <Street></Street>
                    <PostCode></PostCode>
                    <City></City>
                    <CountryCode>BE</CountryCode>
                    <EmailAddress>jsmith@mail.com</EmailAddress>
                    <Phone>+32475123456</Phone>
                </ns2:Declarant>
                <ns2:Period>
                    <ns2:Month>12</ns2:Month>
                    <ns2:Year>2019</ns2:Year>
                </ns2:Period>
                <ns2:IntraClient SequenceNumber="1">
                    <ns2:CompanyVATNumber issuedBy="FR">23334175221</ns2:CompanyVATNumber>
                    <ns2:Code>L</ns2:Code>
                    <ns2:Amount>600.00</ns2:Amount>
                </ns2:IntraClient>
                <ns2:IntraClient SequenceNumber="2">
                    <ns2:CompanyVATNumber issuedBy="FR">23334175221</ns2:CompanyVATNumber>
                    <ns2:Code>T</ns2:Code>
                    <ns2:Amount>500.00</ns2:Amount>
                </ns2:IntraClient>
                <ns2:IntraClient SequenceNumber="3">
                    <ns2:CompanyVATNumber issuedBy="FR">23334175221</ns2:CompanyVATNumber>
                    <ns2:Code>S</ns2:Code>
                    <ns2:Amount>700.00</ns2:Amount>
                </ns2:IntraClient>
                <ns2:IntraClient SequenceNumber="4">
                    <ns2:CompanyVATNumber issuedBy="DE">123456788</ns2:CompanyVATNumber>
                    <ns2:Code>T</ns2:Code>
                    <ns2:Amount>500.00</ns2:Amount>
                </ns2:IntraClient>
                <ns2:IntraClient SequenceNumber="5">
                    <ns2:CompanyVATNumber issuedBy="DE">123456788</ns2:CompanyVATNumber>
                    <ns2:Code>S</ns2:Code>
                    <ns2:Amount>700.00</ns2:Amount>
                </ns2:IntraClient>
                </ns2:IntraListing>
            </ns2:IntraConsignment>
                '''
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[self.report.custom_handler_model_name].export_to_xml_sales_report(options)['file_content']),
            self.get_xml_tree_from_string(expected_xml)
        )

    @freeze_time('2019-12-31')
    def test_be_ec_sales_report_refund(self):
        l_tax = self.env['account.tax'].search([('name', '=', '0% EU M'), ('company_id', '=', self.env.company.id)], limit=1)
        t_tax = self.env['account.tax'].search([('name', '=', '0% EU T'), ('company_id', '=', self.env.company.id)], limit=1)
        s_tax = self.env['account.tax'].search([('name', '=', '0% EU S'), ('company_id', '=', self.env.company.id)], limit=1)

        self._create_invoices([(self.partner_a, l_tax, 100), (self.partner_a, t_tax, 90), (self.partner_a, s_tax, 80)])
        self._create_invoices([(self.partner_a, l_tax, 42), (self.partner_a, t_tax, 42), (self.partner_a, s_tax, 42)], is_refund=True)

        options = self.report.get_options({'date': {'mode': 'range', 'filter': 'this_month'}})
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            # pylint: disable=C0326
            #   Partner                country code,            VAT Number,              Tax         Amount
            [   0,                     1,                       2,                       3,          4],
            [
                (self.partner_a.name,  self.partner_a.vat[:2],  self.partner_a.vat[2:],  'L (46L)',  58.0),
                (self.partner_a.name,  self.partner_a.vat[:2],  self.partner_a.vat[2:],  'T (46T)',  48.0),
                (self.partner_a.name,  self.partner_a.vat[:2],  self.partner_a.vat[2:],  'S (44)',   38.0),
                ('Total',              '',                      '',                      '',        144.0),
            ],
            options,
        )

    @freeze_time('2019-12-31')
    def test_ec_sales_report_month_only(self):
        options = self.report.get_options({'date': {'date_to': '2025-06-30', 'mode': 'range', 'filter': 'custom_return_period'}})
        xml_string = self.env[self.report.custom_handler_model_name].export_to_xml_sales_report(options)['file_content']
        xml_tree = self.get_xml_tree_from_string(xml_string)

        namespaces = {'ns2': 'http://www.minfin.fgov.be/IntraConsignment'}
        month_node = xml_tree.find('.//ns2:Period/ns2:Month', namespaces)
        self.assertIsNotNone(month_node, "The <ns2:Month> element was not found in the <ns2:Period> section.")
        self.assertEqual(month_node.text, '6', "The <ns2:Month> element does not have the expected value.")

    @freeze_time('2019-12-31')
    def test_ec_sales_report_without_country_code(self):
        self.company.vat = '0477472701'

        l_tax = self.env['account.chart.template'].ref('attn_VAT-OUT-00-EU-L')
        self._create_invoices([
            (self.partner_a, l_tax, 300),
        ])
        options = self.report.get_options({'date': {'mode': 'range', 'filter': 'this_month'}})
        expected_xml = '''
            <ns2:IntraConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/IntraConsignment" IntraListingsNbr="1">
                <ns2:IntraListing SequenceNumber="1" ClientsNbr="1" DeclarantReference="___ignore___" AmountSum="300.00">
                    <ns2:Declarant>
                        <VATNumber>0477472701</VATNumber>
                        <Name>company_1_data</Name>
                        <Street></Street>
                        <PostCode></PostCode>
                        <City></City>
                        <CountryCode>BE</CountryCode>
                        <EmailAddress>jsmith@mail.com</EmailAddress>
                        <Phone>+32475123456</Phone>
                    </ns2:Declarant>
                    <ns2:Period>
                        <ns2:Month>12</ns2:Month>
                        <ns2:Year>2019</ns2:Year>
                    </ns2:Period>
                    <ns2:IntraClient SequenceNumber="1">
                        <ns2:CompanyVATNumber issuedBy="FR">23334175221</ns2:CompanyVATNumber>
                        <ns2:Code>L</ns2:Code>
                        <ns2:Amount>300.00</ns2:Amount>
                    </ns2:IntraClient>
                </ns2:IntraListing>
            </ns2:IntraConsignment>
        '''
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[self.report.custom_handler_model_name].export_to_xml_sales_report(options)['file_content']),
            self.get_xml_tree_from_string(expected_xml)
        )

    @freeze_time('2019-12-31')
    def test_be_ec_sales_report_northern_ireland_customer(self):
        """ Ensure services sales are excluded from the EC Sales List report if the
            sale is to a Northern Ireland Customer
        """
        xi_partner = self.env['res.partner'].create([{
            'country_id': self.env.ref('base.uk').id,
            'name': 'XI Partner',
            'vat': 'XI123456782',
        }])

        self._create_invoices([(xi_partner, self.l_tax, 100), (xi_partner, self.s_tax, 80)])

        options = self.report.get_options({'date': {'mode': 'range', 'filter': 'this_month'}})
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Partner                country code,            VAT Number,              Tax         Amount
            [   0,                     1,                       2,                       3,          4],
            [
                (xi_partner.name,      xi_partner.vat[:2],      xi_partner.vat[2:],     'L (46L)',   100.0),
                ('Total',              '',                      '',                     '',          100.0),
            ],
            options,
        )

    @freeze_time('2019-12-31')
    def test_ec_sales_report_same_vat_partners(self):
        self.partner.country_id = self.partner_a.country_id
        self.partner.vat = 'FR23334175221'
        self.partner_a.vat = self.partner_b.vat

        l_tax = self.env['account.tax'].search([('name', '=', '0% EU M'), ('company_id', '=', self.env.company.id)], limit=1)
        self._create_invoices([(self.partner_a, l_tax, 100), (self.partner_b, l_tax, 10), (self.partner, l_tax, 1)])

        options = self.report.get_options({'date': {'mode': 'range', 'filter': 'this_month'}})
        expected_xml = '''
             <ns2:IntraConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/IntraConsignment" IntraListingsNbr="1">
                <ns2:IntraListing SequenceNumber="1" ClientsNbr="2" DeclarantReference="___ignore___" AmountSum="111.00">
                <ns2:Declarant>
                    <VATNumber>0477472701</VATNumber>
                    <Name>company_1_data</Name>
                    <Street></Street>
                    <PostCode></PostCode>
                    <City></City>
                    <CountryCode>BE</CountryCode>
                    <EmailAddress>jsmith@mail.com</EmailAddress>
                    <Phone>+32475123456</Phone>
                </ns2:Declarant>
                <ns2:Period>
                    <ns2:Month>12</ns2:Month>
                    <ns2:Year>2019</ns2:Year>
                </ns2:Period>
                <ns2:IntraClient SequenceNumber="1">
                    <ns2:CompanyVATNumber issuedBy="DE">123456788</ns2:CompanyVATNumber>
                    <ns2:Code>L</ns2:Code>
                    <ns2:Amount>110.00</ns2:Amount>
                </ns2:IntraClient>
                <ns2:IntraClient SequenceNumber="2">
                    <ns2:CompanyVATNumber issuedBy="FR">23334175221</ns2:CompanyVATNumber>
                    <ns2:Code>L</ns2:Code>
                    <ns2:Amount>1.00</ns2:Amount>
                </ns2:IntraClient>
                </ns2:IntraListing>
            </ns2:IntraConsignment>

        '''
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[self.report.custom_handler_model_name].export_to_xml_sales_report(options)['file_content']),
            self.get_xml_tree_from_string(expected_xml)
        )
