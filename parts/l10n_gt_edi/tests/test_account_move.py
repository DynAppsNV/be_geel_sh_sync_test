from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nGtEdi(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('gt')
    def setUpClass(cls):
        super().setUpClass()

    def test_nabn_available_only_for_vendor_credit_note(self):
        vendor_bill = self._create_invoice(move_type='in_invoice', company_id=self.company.id)
        vendor_bill_types = set(vendor_bill.l10n_gt_edi_available_doc_types.split(','))
        self.assertNotIn('NABN', vendor_bill_types)

        vendor_credit_note = self._create_invoice(move_type='in_refund', company_id=self.company.id)
        vendor_credit_note_types = set(vendor_credit_note.l10n_gt_edi_available_doc_types.split(','))
        self.assertIn('NABN', vendor_credit_note_types)

    def test_purchase_document_types_not_filtered_by_affiliation(self):
        move = self._create_invoice(move_type='in_invoice', company_id=self.company.id)
        available_types = set(move.l10n_gt_edi_available_doc_types.split(','))
        self.assertIn('FPEQ', available_types)
        self.assertIn('FCAP', available_types)
