from freezegun import freeze_time
from .common import TestMxEdiCommon
from odoo.tests import tagged, Form


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIAccountMove(TestMxEdiCommon):

    @freeze_time('2017-01-01')
    def test_extra_print_items(self):
        invoice = self._create_invoice()
        print_items_before = invoice.get_extra_print_items()
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        print_items_after = invoice.get_extra_print_items()
        self.assertEqual(len(print_items_before) + 1, len(print_items_after))

    @freeze_time('2017-01-01')
    def test_get_invoice_legal_documents_cfdi(self):
        invoice_with_cfdi = self._create_invoice()
        invoice_without_cfdi = self._create_invoice()
        with self.with_mocked_pac_sign_success():
            invoice_with_cfdi._l10n_mx_edi_cfdi_invoice_try_send()
        self.assertEqual(invoice_with_cfdi._get_invoice_legal_documents('cfdi'), {
            'filename': invoice_with_cfdi.l10n_mx_edi_cfdi_attachment_id.name,
            'filetype': 'xml',
            'content': invoice_with_cfdi.l10n_mx_edi_cfdi_attachment_id.raw,
        })
        self.assertFalse(invoice_without_cfdi._get_invoice_legal_documents('cfdi'))

    def test_cfdi_origin(self):
        """ Test that the l10n_mx_edi_cfdi_origin field can be set correctly. """
        invoice = self._create_invoice(move_type='out_refund')
        invoice.l10n_mx_edi_cfdi_origin = '01|E19C50D2-1292-5817-BDDE-2666967C7471'
        invoice._l10n_mx_edi_get_refund_original_invoices()
        self.assertEqual(invoice.l10n_mx_edi_cfdi_origin, '01|E19C50D2-1292-5817-BDDE-2666967C7471')

    @freeze_time('2017-01-01')
    def test_invoice_tax_objects_required(self):
        """Test that the invoice can be save, when there is a move line with a total amount of 0 that without its field tax objects set"""
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_mx.id,
            'currency_id': self.comp_curr.id,
        })
        with Form(invoice) as f:
            with f.invoice_line_ids.new() as line:
                line.price_unit = 0
