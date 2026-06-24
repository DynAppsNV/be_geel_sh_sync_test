from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class GermanTaxReportTest(AccountSalesReportCommon):

    @classmethod
    @AccountSalesReportCommon.setup_chart_template('de_skr04')
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({
            'country_id': cls.env.ref('base.de').id,
            'vat': 'DE123456788',
            'state_id': cls.env.ref('base.state_de_th').id,
            'l10n_de_stnr': '151/815/08156',
        })

        tax_19_sale = cls.env['account.chart.template'].ref('tax_ust_19_skr04')
        tax_7_sale = cls.env['account.chart.template'].ref('tax_ust_7_skr04')
        tax_eu_sale = cls.env['account.chart.template'].ref('tax_free_skr04_mit_vst')
        tax_export = cls.env['account.chart.template'].ref('tax_export_skr04')
        tax_19_eu_purchase = cls.env['account.chart.template'].ref('tax_eu_19_purchase_skr04')
        tax_7_eu_purchase = cls.env['account.chart.template'].ref('tax_eu_7_purchase_skr04')
        tax_19_purchase = cls.env['account.chart.template'].ref('tax_vst_19_skr04')
        tax_7_purchase = cls.env['account.chart.template'].ref('tax_vst_7_skr04')
        foreign_goods = cls.env['account.chart.template'].ref('tax_ust_19_13b_ausland_ohne_vst_skr04')

        moves = cls.env['account.move'].create(
            [
                {
                    'move_type': 'out_invoice',
                    'partner_id': cls.partner_a.id,
                    'invoice_date': '2019-11-01',
                    'invoice_line_ids': [
                        Command.create({
                            'price_unit': 150,
                            'tax_ids': tax_19_sale.ids,
                        })
                    ],
                },
                {
                    'move_type': 'out_invoice',
                    'partner_id': cls.partner_a.id,
                    'invoice_date': '2019-11-01',
                    'invoice_line_ids': [
                        Command.create({
                            'price_unit': 200,
                            'tax_ids': tax_7_sale.ids,
                        })
                    ],
                },
                {
                    'move_type': 'out_invoice',
                    'partner_id': cls.partner_a.id,
                    'invoice_date': '2019-11-01',
                    'invoice_line_ids': [
                        Command.create({
                            'price_unit': 500,
                            'tax_ids': tax_eu_sale.ids,
                        })
                    ],
                },
                {
                    'move_type': 'out_invoice',
                    'partner_id': cls.partner_a.id,
                    'invoice_date': '2019-11-01',
                    'invoice_line_ids': [
                        Command.create({
                            'price_unit': 300,
                            'tax_ids': tax_export.ids,
                        })
                    ],
                },
                {
                    'move_type': 'in_invoice',
                    'partner_id': cls.partner_a.id,
                    'invoice_date': '2019-11-01',
                    'invoice_line_ids': [
                        Command.create({
                            'price_unit': 75,
                            'tax_ids': tax_19_eu_purchase.ids,
                        })
                    ],
                },
                {
                    'move_type': 'in_invoice',
                    'partner_id': cls.partner_a.id,
                    'invoice_date': '2019-11-01',
                    'invoice_line_ids': [
                        Command.create({
                            'price_unit': 120,
                            'tax_ids': tax_7_eu_purchase.ids,
                        })
                    ],
                },
                {
                    'move_type': 'in_invoice',
                    'partner_id': cls.partner_a.id,
                    'invoice_date': '2019-11-01',
                    'invoice_line_ids': [
                        Command.create({
                            'price_unit': 400,
                            'tax_ids': tax_19_purchase.ids,
                        })
                    ],
                },
                {
                    'move_type': 'in_invoice',
                    'partner_id': cls.partner_a.id,
                    'invoice_date': '2019-11-01',
                    'invoice_line_ids': [
                        Command.create({
                            'price_unit': 100,
                            'tax_ids': tax_7_purchase.ids,
                        })
                    ],
                },
                {
                    'move_type': 'in_invoice',
                    'partner_id': cls.partner_a.id,
                    'invoice_date': '2019-11-01',
                    'invoice_line_ids': [
                        Command.create(
                            {
                                'price_unit': 50,
                                'tax_ids': foreign_goods.ids,
                            }
                        )
                    ],
                },
            ]
        )
        moves.action_post()

    @freeze_time('2019-12-31')
    def test_generate_xml(self):
        report = self.env.ref('l10n_de.tax_report')
        options = report.get_options({})

        expected_xml = """
        <Anmeldungssteuern art="UStVA" version="2019">
            <Erstellungsdatum>20191231</Erstellungsdatum>
            <DatenLieferant>
                <Name>company_1_data</Name>
                <Strasse />
                <PLZ />
                <Ort />
                <Telefon>+32475123456</Telefon>
                <Email>jsmith@mail.com</Email>
            </DatenLieferant>
            <Steuerfall>
                <Unternehmer>
                    <Bezeichnung>company_1_data</Bezeichnung>
                    <Str />
                    <Ort />
                    <PLZ />
                    <Telefon>+32475123456</Telefon>
                    <Email>jsmith@mail.com</Email>
                </Unternehmer>
                <Umsatzsteuervoranmeldung>
                    <Jahr>2019</Jahr>
                    <Zeitraum>11</Zeitraum>
                    <Steuernummer>4151081508156</Steuernummer>
                    <Kz43>800</Kz43>
                    <Kz61>22.65</Kz61>
                    <Kz66>83.00</Kz66>
                    <Kz67>9.50</Kz67>
                    <Kz81>150</Kz81>
                    <Kz84>50</Kz84>
                    <Kz85>9.50</Kz85>
                    <Kz86>200</Kz86>
                    <Kz89>75</Kz89>
                    <Kz93>120</Kz93>
                </Umsatzsteuervoranmeldung>
            </Steuerfall>
        </Anmeldungssteuern>
        """
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self.env[report.custom_handler_model_name].export_tax_report_to_xml(options)['file_content']),
            self.get_xml_tree_from_string(expected_xml)
        )
