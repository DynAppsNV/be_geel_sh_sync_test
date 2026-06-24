# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo.addons.l10n_br_avatax.tests.test_br_avatax import TestAvalaraBrCommon
from odoo.tests import tagged


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestAvalaraBrInvoiceFiscalReform(TestAvalaraBrCommon):
    def test_01_invoice_br_fiscal_reform(self):
        """Set all the new fields for the fiscal reform and verify if the generated request is correct."""
        invoice, _ = self._create_invoice_01_and_expected_response()
        invoice.company_id.l10n_br_is_icbs = True
        invoice.l10n_br_presence = '2'
        invoice.l10n_br_goods_operation_type_id.l10n_br_customs_regime_id = self.env.ref('l10n_br_edi_fiscal_reform.customs_regime_capital_goods')

        self.product_user.write({
            'l10n_br_nbs_id': self.env.ref('l10n_br_edi_fiscal_reform.nbs_101'),
            'l10n_br_legal_uom_id': self.env.ref('uom.product_uom_dozen'),
        })

        invoice.partner_id.write({
            'l10n_br_tax_regime': 'simplified',
            'l10n_br_is_cbs_ibs_normal': False,
            'l10n_br_cbs_credit': 5,
            'l10n_br_ibs_credit': 10,
        })

        invoice.invoice_line_ids[0].l10n_br_cbs_ibs_deduction = 7

        # The fiscal reform modules don't change how responses are handled, so use a dummy tax response without any taxes in it.
        with self._with_mocked_l10n_br_iap_request([("calculate_tax", "fiscal_reform_request_goods", "dummy_tax_response")]):
            invoice.button_external_tax_calculation()

        # Test service invoice as well.
        invoice.partner_id.l10n_br_tax_regime = 'individual'
        invoice.partner_id.city_id = self.env['res.city'].create({
            'name': 'test',
            'country_id': self.env.ref('base.br').id
        })
        invoice.invoice_line_ids.mapped('product_id').write({
            'type': 'service',
            'l10n_br_property_service_code_origin_id': self.env['l10n_br.service.code'].create({
                'code': '123',
                'city_id': invoice.partner_id.city_id.id
            }).id
        })
        invoice.l10n_latam_document_type_id = self.env.ref('l10n_br.dt_SE')
        invoice.l10n_br_goods_operation_type_id = self.env.ref('l10n_br_edi_fiscal_reform.operation_type_sales_other_services_onerous')
        invoice.l10n_br_goods_operation_type_id.l10n_br_service_operation_indicator = '432'

        with self._with_mocked_l10n_br_iap_request([("calculate_tax", "fiscal_reform_request_services", "dummy_tax_response")]):
            invoice.button_external_tax_calculation()

    def test_02_informative_taxes(self):
        invoice, response = self._create_invoice_01_and_expected_response()
        invoice.company_id.l10n_br_is_icbs = True

        # Replace an informative tax with a new fiscal reform one.
        invoice.l10n_br_edi_avatax_data = json.dumps(response).replace("aproxtribState", "cbs")

        rio_city = self.env.ref("l10n_br.city_br_002")
        invoice.invoice_line_ids.mapped("product_id").write(
            {
                "type": "service",
                "l10n_br_property_service_code_origin_id": self.env["l10n_br.service.code"].create(
                    {"code": "12345", "city_id": rio_city.id}
                ),
            }
        )
        invoice.partner_id.city_id = rio_city
        invoice.l10n_latam_document_type_id = self.env.ref("l10n_br.dt_SE")

        payload = invoice._l10n_br_prepare_invoice_payload()

        for line in payload['lines']:
            self.assertTrue(
                any(detail['taxType'] == 'cbs' for detail in line['taxDetails']),
                "CBS tax should remain in the taxDetails, even though it's informative."
            )

        self.assertIn(
            'cbs',
            payload['summary']['taxByType'],
            "CBS tax should remain in the summary, even though it's informative."
        )

        self.assertTrue(
            any(tax['taxType'] == 'cbs' for tax in payload['summary']['taxImpactHighlights']['informative']),
            "CBS tax should remain in the highlights, even though it's informative."
        )
