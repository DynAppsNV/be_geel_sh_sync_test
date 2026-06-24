from odoo import Command, fields
from odoo.tests import tagged, patch
from odoo.addons.account.tools.structured_reference import is_valid_structured_reference_for_country
from odoo.addons.account_online_synchronization.tests.common import AccountOnlineSynchronizationCommon


@tagged('post_install', '-at_install')
class TestAccountOnlinePaymentBatch(AccountOnlineSynchronizationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'BE68539007547034',
            'acc_type': 'iban',
            'allow_out_payment': True,
            'partner_id': cls.partner.id,
        })

        cls.company_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'BE32707171912447',
            'acc_type': 'iban',
            'partner_id': cls.env.company.partner_id.id,
        })
        cls.euro_bank_journal.bank_account_id = cls.company_bank

        sepa_ct = cls.env.ref('account_iso20022.account_payment_method_sepa_ct')
        cls.sepa_method_line = cls.euro_bank_journal.outbound_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id == sepa_ct,
        )[0]

    @patch('odoo.addons.account_online_payment.models.account_batch_payment.is_valid_structured_reference_for_country', side_effect=is_valid_structured_reference_for_country)
    def test_prepare_payment_data(self, mock):
        """
        IMPORTANT: The idea behind this test is to ensure that Enterprise and Odoofin communicate correctly.

        If this test breaks, it doesn't necessarily mean that the code in account_online_payment is wrong,
        but rather that the data being sent to Odoofin has changed and Odoofin might need to be updated to
        handle the new data structure.

        If that is the case, please update Odoofin's side to handle the new data structure.
        """
        payment = self.env['account.payment'].create({
            'partner_id': self.partner.id,
            'partner_bank_id': self.partner_bank.id,
            'amount': 100.0,
            'payment_type': 'outbound',
            'journal_id': self.euro_bank_journal.id,
            'payment_method_line_id': self.sepa_method_line.id,
        })
        payment.action_post()

        batch = self.env['account.batch.payment'].create({
            'batch_type': 'outbound',
            'journal_id': self.euro_bank_journal.id,
            'payment_ids': [Command.set(payment.ids)],
        })

        self.partner.vat = 'vat'
        self.partner.contact_address_inline = 'contact_address_inline'
        batch.journal_id.company_id.vat = 'vat'

        data = batch._prepare_payment_data()

        self.assertEqual(data, {
            'account_id': self.account_online_account.online_identifier,
            'batch_booking': batch.iso20022_batch_booking,
            'date': fields.Date.to_string(batch.date),
            'payer_account_number': batch.journal_id.account_online_account_id.account_number,
            'payer_address': batch.journal_id.company_id.partner_id.contact_address_inline,
            'payer_name': batch.journal_id.company_id.name,
            'payer_identification': batch.journal_id.company_id.vat,
            'payment_type': "bulk",
            'payments': [{
                'amount': 100.0,
                'account_number': self.partner_bank.sanitized_acc_number,
                'account_type': 'IBAN',
                'creditor_address': 'contact_address_inline',
                'creditor_identification': 'vat',
                'creditor_name': self.partner.name,
                'currency': payment.currency_id.display_name,
                'date': fields.Date.to_string(payment.date),
                'reference': payment.memo,
                'structured_reference': is_valid_structured_reference_for_country(payment.memo, 'BE'),
                'end_to_end_uuid': payment.end_to_end_uuid,
            }],
            'reference': batch.name,
        })
        mock.assert_called_once_with(payment.memo, 'BE')
