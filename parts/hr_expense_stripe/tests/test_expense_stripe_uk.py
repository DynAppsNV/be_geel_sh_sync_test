from odoo.exceptions import UserError

from odoo.addons.hr_expense_stripe.tests.common import TestExpenseStripeCommon


class TestExpenseStripeUK(TestExpenseStripeCommon):  # We inherit from the EU test class to reuse some tests
    @classmethod
    def setup_references(cls):
        # OVERRIDE TestExpenseStripeCommon
        return 'base.uk', 'base.GBP'

    #####################################
    #        Test Common Actions        #
    #####################################
    def test_create_account(self):
        super().test_create_account()

    def test_configure_account(self):
        super().test_configure_account()

    def test_refresh_account(self):
        super().test_refresh_account()

    def test_create_card(self):
        super().test_create_card()

    def test_virtual_card(self):
        super().test_virtual_card()

    def test_physical_card_no_shipping(self):
        super().test_physical_card_no_shipping()

    def test_create_cardholder_no_user(self):
        super().test_create_cardholder_no_user()

    def test_create_cardholder(self):
        super().test_create_cardholder()

    #####################################
    #        Test Common Webhooks       #
    #####################################
    def test_webhook_balance_available_event(self):
        super().test_webhook_balance_available_event()

    def test_webhook_issuing_authorization_request_event(self):
        super().test_webhook_issuing_authorization_request_event()

    def test_webhook_issuing_authorization_created_event(self):
        super().test_webhook_issuing_authorization_created_event()

    def test_webhook_issuing_authorization_updated_event(self):
        super().test_webhook_issuing_authorization_updated_event()

    def test_webhook_issuing_card_updated_event(self):
        super().test_webhook_issuing_card_updated_event()

    def test_webhook_issuing_transaction_created_event(self):
        super().test_webhook_issuing_transaction_created_event()

    def test_webhook_issuing_transaction_updated_event(self):
        super().test_webhook_issuing_transaction_updated_event()

    def test_webhook_issuing_authorization_updated_event_amount_zero(self):
        super().test_webhook_issuing_authorization_updated_event_amount_zero()

    def test_webhook_topup_succeeded_event(self):
        super().test_webhook_topup_succeeded_event()

    def test_physical_card_shipping(self):
        super().test_physical_card_shipping()

    def test_stripe_expense_card_without_spending_policy_interval(self):
        super().test_stripe_expense_card_without_spending_policy_interval()

    #####################################
    #           Test Actions            #
    #####################################
    def test_funding_instructions_uk(self):
        """ Test fetching the funding instructions for a european company
        MUST BE SYNC WITH THE TEST IN test_expense_stripe_eu.py:test_funding_instructions_eu
        """
        united_kingdom = self.stripe_country
        self.setup_account_creation()
        self.assertRecordValues(self.stripe_journal, [
            {'currency_id': self.stripe_currency.id, 'stripe_issuing_balance': 0.0, 'stripe_issuing_balance_timestamp': 0.0},
        ])

        expected_calls = [{
            'route': 'funding_instructions',
            'method': 'POST',  # Even though it's technically a GET request, it generates the new data on Stripe if updated
            'payload': {
                'account': 'acct_1234567890',
                'bank_transfer': {'type': 'gb_bank_transfer'},
                'currency': 'GBP',
                'funding_type': 'bank_transfer',
            },
            'return_data': {
                'currency': 'gbp',
                'bank_transfer': {
                    'country': 'GB',
                    'financial_addresses': [{
                        'sort_code': {
                            'account_number': '01234567',
                            'account_holder_address': {
                                'city': 'London',
                                'country': 'GB',
                                "line1": '1st floor, 1 street',
                                'line2': 'A 1',
                                'postal_code': 'WC2N5DU',
                                'state': 'London'
                            },
                            'sort_code': '123456',
                            'account_holder_name': 'TEST STRIPE',
                            'bank_address': {
                                'city': 'Londinium',
                                'country': 'GB',
                                "line1": '2nd floor, 2 street',
                                'line2': 'A 2',
                                'postal_code': 'XC2N5DX',
                                'state': 'London'
                            },
                        },
                        'type': 'sort_code',
                        'supported_networks': ['bacs', 'fps'],
                    }],
                },
                'livemode': False,
            }
        }]

        with self.patch_stripe_requests('models.account_journal', expected_calls):
            action = self.stripe_journal.action_open_topup_wizard()

            partner_account = self.env['res.partner.bank'].search([('acc_number', '=', '01234567')])
            partner = partner_account.partner_id
            bank = partner_account.bank_id
            self.assertRecordValues(partner_account, [
                {'clearing_number': '123456', 'bank_name': 'Stripe Partner Bank', 'country_code': 'GB', 'currency_id': self.stripe_currency.id},
            ])
            self.assertRecordValues(partner, [
                {'name': 'TEST STRIPE', 'street': '1st floor, 1 street', 'street2': 'A 1', 'city': 'London', 'zip': 'WC2N5DU', 'country_id': united_kingdom.id},
            ])
            self.assertRecordValues(bank, [
                {'street': '2nd floor, 2 street', 'street2': 'A 2', 'city': 'Londinium', 'zip': 'XC2N5DX', 'country': united_kingdom.id}
            ])
            wizard = self.env['hr.expense.stripe.topup.wizard'].browse(action['res_id'])
            with self.assertRaises(UserError):
                # EU countries are restricted to pushing funds to the Stripe account
                wizard.action_topup()
