# -*- coding: utf-8 -*
from odoo import Command
from odoo.tests import tagged
from odoo.tools import file_open
from .common import TestPeEdiCommon, mocked_l10n_pe_edi_post_invoice_web_service
from unittest.mock import patch

from freezegun import freeze_time
from lxml import etree


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiXmls(TestPeEdiCommon):

    def test_price_amount_rounding(self):
        with freeze_time(self.frozen_today), \
            patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_invoice(invoice_line_ids=[(0, 0, {
                'product_id': self.product.id,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 83.6,  # We will compute 250.8 / 3, which results in 83.60000000000001. It must be rounded.
                'quantity': 3,
                'tax_ids': [(6, 0, self.tax_18.ids)],
            })])
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            etree = self.get_xml_tree_from_string(edi_xml)
            price_amount = etree.find('.//{*}InvoiceLine/{*}Price/{*}PriceAmount')
            self.assertEqual(price_amount.text, '83.6')

    def test_invoice_simple_case(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_invoice()
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)
            expected_etree = self.get_xml_tree_from_string(self.expected_invoice_xml_values)
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_refund_simple_case(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_refund()
            (move.reversed_entry_id + move).action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)
            expected_etree = self.get_xml_tree_from_string(self.expected_refund_xml_values)
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_debit_note_simple_case(self):
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_debit_note()
            (move.debit_origin_id + move).action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)
            expected_etree = self.get_xml_tree_from_string(self.expected_debit_note_xml_values)
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_payment_term_detraction_case(self):
        """ Invoice in USD with detractions and multiple payment term lines"""
        self.product.l10n_pe_withhold_percentage = 10
        self.product.l10n_pe_withhold_code = '001'
        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            update_vals_dict = {"l10n_pe_edi_operation_type": "1001",
                                "invoice_payment_term_id": self.env.ref("account.account_payment_term_advance_60days").id}
            invoice = self._create_invoice(**update_vals_dict).with_context(edi_test_mode=True)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)

        with file_open('l10n_pe_edi/tests/test_files/invoice_detraction_payment_terms.xml', 'rb') as expected_file:
            expected_etree = self.get_xml_tree_from_string(expected_file.read())
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_detraction_with_decimal(self):
        """ Invoice in PEN with detraction containing decimal digits"""
        self.product.l10n_pe_withhold_percentage = 10
        self.product.l10n_pe_withhold_code = '019'

        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            vals = {
                'name': 'F FFI-%s1' % self.time_name,
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2017-01-01',
                'date': '2017-01-01',
                'invoice_payment_term_id': self.env.ref("account.account_payment_term_end_following_month").id,
                'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
                'l10n_pe_edi_operation_type': '1001',
                'invoice_line_ids': [Command.create({
                    'product_id': self.product.id,
                    'price_unit': 990.0,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_18.ids)],
                })],
            }
            invoice = self.env['account.move'].create(vals).with_context(edi_test_mode=True)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)

        with file_open('l10n_pe_edi/tests/test_files/invoice_detraction_with_decimal.xml', 'rb') as expected_invoice_file:
            expected_etree = self.get_xml_tree_from_string(expected_invoice_file.read())
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_detraction_with_decimal_foreign_currency(self):
        """ Invoice in USD with detraction containing decimal digits"""
        self.product.l10n_pe_withhold_percentage = 10
        self.product.l10n_pe_withhold_code = '019'

        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            vals = {
                'name': 'F FFI-%s1' % self.time_name,
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2017-01-01',
                'date': '2017-01-01',
                'currency_id': self.other_currency.id,
                'invoice_payment_term_id': self.env.ref("account.account_payment_term_end_following_month").id,
                'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
                'l10n_pe_edi_operation_type': '1001',
                'invoice_line_ids': [Command.create({
                    'product_id': self.product.id,
                    'price_unit': 990.0,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_18.ids)],
                })],
            }
            invoice = self.env['account.move'].create(vals).with_context(edi_test_mode=True)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)

        with file_open('l10n_pe_edi/tests/test_files/invoice_detraction_with_decimal_foreign_currency.xml', 'rb') as expected_invoice_file:
            expected_etree = self.get_xml_tree_from_string(expected_invoice_file.read())
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_low_unit_price_with_higher_decimal_precision(self):
        """ Invoice with a decimal precition of 4 digits for the product price
            and a non-zero unit price that is rounded to 0.00 in the decimal
            precision of the currency.
        """
        self.env.ref('product.decimal_price').digits = 4
        self.currency.rounding = 0.01
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            invoice_line_vals = {
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                        'price_unit': 0.0045,
                        'quantity': 100,
                        'tax_ids': [Command.set(self.tax_18.ids)],
                    })
                ],
            }
            move = self._create_invoice(**invoice_line_vals)
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)

            with file_open('l10n_pe_edi/tests/test_files/invoice_low_unit_price.xml', 'rb') as expected_file:
                expected_etree = self.get_xml_tree_from_string(expected_file.read())

            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_free(self):
        """ Test the UBL generated for an invoice that uses the '18% Free' tax
        (feature introduced in enterprise#56767)
        """
        tax_18_free = self.env['account.chart.template'].ref('tax_free_group')
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_invoice(
                l10n_pe_edi_legend='1002',
                invoice_line_ids=[(0, 0, {
                    'product_id': self.product.id,
                    'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                    'price_unit': 2000.0,
                    'quantity': 5,
                    'discount': 20.0,
                    'tax_ids': [(6, 0, tax_18_free.ids)],
                })],
            )
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)

            with file_open('l10n_pe_edi/tests/test_files/invoice_free.xml', 'rb') as expected_file:
                expected_etree = self.get_xml_tree_from_string(expected_file.read())

            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_isc(self):
        """ Test the UBL generated for an invoice that uses both the ISC and the IGV taxes.
        (feature introduced in enterprise#35280)
        """
        tax_isc = self.env['account.tax'].create({
            'name': 'tax_ics_20',
            'sequence': -1,  # So it precedes the IGV 18% tax
            'amount_type': 'percent',
            'amount': 20,
            'include_base_amount': True,
            'l10n_pe_edi_isc_type': '01',
            'l10n_pe_edi_tax_code': '2000',
            'l10n_pe_edi_unece_category': 'S',
            'type_tax_use': 'sale',
            'tax_group_id': self.env['account.chart.template'].ref('tax_group_isc').id,
        })
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_invoice(
                invoice_line_ids=[
                    (0, 0, {
                        'product_id': self.product.id,
                        'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                        'price_unit': 2000.0,
                        'quantity': 5,
                        'discount': 20.0,
                        'tax_ids': [(6, 0, [tax_isc.id, self.tax_18.id])],
                    }),
                    (0, 0, {
                        'product_id': self.product.id,
                        'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                        'price_unit': 2000.0,
                        'quantity': 5,
                        'discount': 20.0,
                        'tax_ids': [(6, 0, [self.tax_18.id])],
                    })
                ],
            )
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)

            with file_open('l10n_pe_edi/tests/test_files/invoice_isc.xml', 'rb') as expected_file:
                expected_etree = self.get_xml_tree_from_string(expected_file.read())
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_global_discount(self):
        """ Invoice in USD with a global and line nevel discount."""
        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            update_vals_dict = {
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                        'price_unit': 2000.0,
                        'quantity': 5,
                        'discount': 20.0,
                        'tax_ids': [(6, 0, self.tax_18.ids)],
                    }),
                    Command.create({
                        "name": "Discount",
                        "price_unit": -200.0,
                        "tax_ids": [Command.set(self.tax_18.ids)]
                    }),
                ],
            }
            invoice = self._create_invoice(**update_vals_dict)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)

        with file_open('l10n_pe_edi/tests/test_files/invoice_global_discount.xml', 'rb') as expected_file:
            expected_etree = self.get_xml_tree_from_string(expected_file.read())
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_down_payment(self):
        """ Invoice with a downpayment on a sale order. Note the downpayment invoice is not different
        than any other invoice which is why we only look at the final invoice XML to make sure all the
        right data is there. """

        if 'sale' not in self.env["ir.module.module"]._installed():
            self.skipTest("Sale module is not installed")

        self.env.user.group_ids |= self.env.ref('sales_team.group_sale_manager')

        with freeze_time(self.frozen_today):
            sale_order = self.env['sale.order'].create({
                'partner_id': self.partner_a.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                        'price_unit': 2000.0,
                        'product_uom_qty': 5,
                        'tax_ids': [(6, 0, self.tax_18.ids)],
                    })
                ]
            })
            sale_order.action_confirm()

            context = {
                'active_model': 'sale.order',
                'active_ids': [sale_order.id],
                'active_id': sale_order.id,
                'default_journal_id': self.company_data['default_journal_sale'].id,
            }
            downpayment_1 = self.env['sale.advance.payment.inv'].with_context(context).create({
                'advance_payment_method': 'fixed',
                'fixed_amount': 115,
            })._create_invoices(sale_order)

            downpayment_2 = self.env['sale.advance.payment.inv'].with_context(context).create({
                'advance_payment_method': 'fixed',
                'fixed_amount': 115,
            })._create_invoices(sale_order)

            final = self.env['sale.advance.payment.inv'].with_context(context).create({})._create_invoices(sale_order)

            with patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
                downpayment_1.action_post()
                downpayment_2.action_post()
                final.action_post()

                generated_files = self._process_documents_web_services(final, {'pe_ubl_2_1'})
                self.assertTrue(generated_files)

        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)
        with file_open('l10n_pe_edi/tests/test_files/invoice_final_downpayment.xml', 'rb') as expected_file:
            expected_etree = self.get_xml_tree_from_string(expected_file.read())
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_down_payment_foreign_currency(self):
        """ Invoice with a downpayment on a sale order. Note the downpayment invoice is not different
        than any other invoice which is why we only look at the final invoice XML to make sure all the
        right data is there. """

        if self.env["ir.module.module"]._get('sale').state != 'installed':
            self.skipTest("Sale module is not installed")
        self.env.user.group_ids += self.env.ref('sales_team.group_sale_salesman')

        pricelist = self.env['product.pricelist'].create({
            'name': 'Test Pricelist',
            'currency_id': self.other_currency.id,
        })

        with freeze_time(self.frozen_today):
            sale_order = self.env['sale.order'].create({
                'partner_id': self.partner_a.id,
                'pricelist_id': pricelist.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                        'price_unit': 2000.0,
                        'product_uom_qty': 5,
                        'tax_ids': [(6, 0, self.tax_18.ids)],
                    }),
                ],
            })
            sale_order.action_confirm()

            context = {
                'active_model': 'sale.order',
                'active_ids': [sale_order.id],
                'active_id': sale_order.id,
                'default_journal_id': self.company_data['default_journal_sale'].id,
            }
            downpayment = self.env['sale.advance.payment.inv'].with_context(context).create({
                'advance_payment_method': 'fixed',
                'fixed_amount': 115,
            })._create_invoices(sale_order)

            final = self.env['sale.advance.payment.inv'].with_context(context).create({})._create_invoices(sale_order)

            with patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
                downpayment.action_post()
                final.action_post()

                generated_files = self._process_documents_web_services(final, {'pe_ubl_2_1'})
                self.assertTrue(generated_files)

        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)
        with file_open('l10n_pe_edi/tests/test_files/invoice_final_downpayment_foreign_currency.xml', 'rb') as expected_file:
            expected_etree = self.get_xml_tree_from_string(expected_file.read())
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_withholding(self):
        """ Invoice with withholding tax associated. There should be only one allowance node
            even though there are two lines with the withholding tax. """
        self.tax_18.include_base_amount = True
        tax_withholding = self.env['account.tax'].create({
            'name': 'tax_withholding',
            'amount_type': 'percent',
            'amount': -3.0,
            'type_tax_use': 'sale',
            'tax_group_id': self.env['account.chart.template'].ref('tax_group_igv_withholding').id,
        })

        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            update_vals_dict = {
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                        'price_unit': 0.481936,
                        'quantity': 300,
                        'tax_ids': [(6, 0, [tax_withholding.id, self.tax_18.id])],
                    }),
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                        'price_unit': 0.747376,
                        'quantity': 300,
                        'tax_ids': [(6, 0, [tax_withholding.id, self.tax_18.id])],
                    }),
                ],
            }
            invoice = self._create_invoice(**update_vals_dict)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)

        with file_open('l10n_pe_edi/tests/test_files/invoice_withholding.xml', 'rb') as expected_file:
            expected_etree = self.get_xml_tree_from_string(expected_file.read())
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_icbper_fixed_tax(self):
        """ Test that an invoice with an ICBPER fixed-amount tax generates EDI XML without errors."""
        tax_icbper = self.env['account.tax'].create({
            'name': 'ICBPER',
            'amount_type': 'fixed',
            'amount': 0.5,
            'l10n_pe_edi_tax_code': '7152',
            'l10n_pe_edi_unece_category': 'S',
            'type_tax_use': 'sale',
            'tax_group_id': self.env['account.chart.template'].ref('tax_group_icbper').id,
        })
        with freeze_time(self.frozen_today), \
             patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            move = self._create_invoice(
                invoice_line_ids=[Command.create({
                    'product_id': self.product.id,
                    'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                    'price_unit': 2000.0,
                    'quantity': 5,
                    'tax_ids': [Command.set([tax_icbper.id])],
                })],
            )
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)

    def test_invoice_foreign_customer(self):
        """Invoice for a foreign customer"""
        co_identification_type = self.env['l10n_latam.identification.type'].sudo().create({
            "name": "Cédula de ciudadanía (CO)",
            "country_id": self.env.ref('base.co').id,
        })
        self.partner_a.write({
            "l10n_latam_identification_type_id": co_identification_type.id,
            "country_id": self.env.ref('base.co').id,
        })
        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            vals = {
                'name': 'F FFI-%s1' % self.time_name,
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2017-01-01',
                'date': '2017-01-01',
                'currency_id': self.other_currency.id,
                'invoice_payment_term_id': self.env.ref("account.account_payment_term_end_following_month").id,
                'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type02').id,
                'l10n_pe_edi_operation_type': '0200',
                'invoice_line_ids': [Command.create({
                    'product_id': self.product.id,
                    'price_unit': 990.0,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_18.ids)],
                })],
            }
            invoice = self.env['account.move'].create(vals).with_context(edi_test_mode=True)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)
        current_etree = self.get_xml_tree_from_string(edi_xml)

        with file_open('l10n_pe_edi/tests/test_files/foreign_customer.xml', 'rb') as expected_invoice_file:
            expected_etree = self.get_xml_tree_from_string(expected_invoice_file.read())
        self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_payment_term_ordering(self):
        """ Instalments (Cuota001/002/003) must be emitted in ascending due-date order.

        When a 3-instalment payment term is used (e.g. 50 % / 30 % / 20 %), the
        resulting cac:PaymentTerms nodes must be sorted by PaymentDueDate, not
        by database row insertion order.  Regression for bug where the amounts
        were mixed up between cuotas.
        """
        payment_term = self.env['account.payment.term'].create({
            'name': '20/30/50 instalment',
            # Lines intentionally created in descending nb_days order so that without the
            # date_maturity sort fix, the DB insertion order would assign Cuota001 to the
            # latest/largest instalment instead of the earliest/smallest one.
            'line_ids': [
                Command.create({'value': 'percent', 'value_amount': 50, 'nb_days': 15}),
                Command.create({'value': 'percent', 'value_amount': 30, 'nb_days': 10}),
                Command.create({'value': 'percent', 'value_amount': 20, 'nb_days': 5}),
            ],
        })

        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_pe_edi.models.account_edi_format.AccountEdiFormat._l10n_pe_edi_post_invoice_web_service',
                   new=mocked_l10n_pe_edi_post_invoice_web_service):
            vals = {
                'name': 'F FFI-%s1' % self.time_name,
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': '2017-01-01',
                'date': '2017-01-01',
                'invoice_payment_term_id': payment_term.id,
                'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
                'invoice_line_ids': [Command.create({
                    'product_id': self.product.id,
                    'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                    'price_unit': 530.0,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.tax_18.ids)],
                })],
            }
            invoice = self.env['account.move'].create(vals).with_context(edi_test_mode=True)
            invoice.action_post()

            generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(generated_files[0])
        invoice_etree = self.get_xml_tree_from_string(edi_xml)

        # Extract only the Cuota instalment nodes (skip the summary FormaPago/Credito node)
        cuota_nodes = [
            node for node in invoice_etree.findall('.//{*}PaymentTerms')
            if (node.findtext('{*}PaymentMeansID') or '').startswith('Cuota')
        ]

        # Wrap extracted nodes in a root element so we can use assertXmlTreeEqual
        generated_root = etree.Element('root')
        for node in cuota_nodes:
            generated_root.append(node)

        expected_root = self.get_xml_tree_from_string(b'''<root
                xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
                xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
            <cac:PaymentTerms>
                <cbc:ID>FormaPago</cbc:ID>
                <cbc:PaymentMeansID>Cuota001</cbc:PaymentMeansID>
                <cbc:Amount currencyID="PEN">125.08</cbc:Amount>
                <cbc:PaymentDueDate>2017-01-06</cbc:PaymentDueDate>
            </cac:PaymentTerms>
            <cac:PaymentTerms>
                <cbc:ID>FormaPago</cbc:ID>
                <cbc:PaymentMeansID>Cuota002</cbc:PaymentMeansID>
                <cbc:Amount currencyID="PEN">187.62</cbc:Amount>
                <cbc:PaymentDueDate>2017-01-11</cbc:PaymentDueDate>
            </cac:PaymentTerms>
            <cac:PaymentTerms>
                <cbc:ID>FormaPago</cbc:ID>
                <cbc:PaymentMeansID>Cuota003</cbc:PaymentMeansID>
                <cbc:Amount currencyID="PEN">312.70</cbc:Amount>
                <cbc:PaymentDueDate>2017-01-16</cbc:PaymentDueDate>
            </cac:PaymentTerms>
        </root>''')
        self.assertXmlTreeEqual(generated_root, expected_root)

    def test_reversal_cancel_reason_mapping(self):
        """Test that the cancel and credit reason in the reversal wizard are correctly mapped to the fields in the Peruvian EDI tab."""

        move = self._create_invoice()
        move.action_post()

        reversal_wizard = self.env['account.move.reversal'].with_context(
            active_model="account.move",
            active_ids=move.ids
        ).create({
            'reason': 'Test reason',
            'journal_id': move.journal_id.id,
            'l10n_pe_edi_refund_reason': '01',
        })
        action = reversal_wizard.reverse_moves()
        reverse_move = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(reverse_move.l10n_pe_edi_cancel_reason, 'Test reason')
        self.assertEqual(reverse_move.l10n_pe_edi_refund_reason, '01')
