# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4

from odoo import fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    iso20022_uetr = fields.Char(
        string='UETR',
        help='Unique end-to-end transaction reference',
    )

    def _get_payments_vals(self, journal_id, payment_date=fields.Date.today()):
        self.ensure_one()
        payments = []
        if journal_id.sepa_pain_version == 'pain.001.001.09':
            if not self.iso20022_uetr:
                iso20022_uetr = self.iso20022_uetr = str(uuid4())
            else:
                iso20022_uetr = self.iso20022_uetr
        else:
            iso20022_uetr = False

        index = 1
        allocations = self.compute_salary_allocations()
        for ba in self.employee_id.bank_account_ids:
            amount = allocations[str(ba.id)]
            if not amount:
                continue
            payment = {
                'id': self.id,
                'name': str(self.id) if len(self.employee_id.bank_account_ids) == 1 else f'{self.id}-{index}',
                'payment_date': payment_date,
                'amount': amount,
                'journal_id': journal_id.id,
                'currency_id': journal_id.currency_id.id,
                'payment_type': 'outbound',
                'memo': str(self.id),
                'partner_id': ba.partner_id.id or self.employee_id.work_contact_id.id,
                'partner_bank_id': ba.id,
                'iso20022_charge_bearer': journal_id.iso20022_charge_bearer,
                # The "High" priority level is a payment attribute that we should specify for salary payments :
                # https://www.febelfin.be/sites/default/files/2019-04/standard-credit_transfer-xml-v32-en_0.pdf
                # section 2.6
                'iso20022_priority': 'HIGH' if journal_id.company_id.account_fiscal_country_id.code == "BE" else 'NORM',
            }
            if iso20022_uetr:
                payment['iso20022_uetr'] = iso20022_uetr
            payments.append(payment)
            index += 1
        return payments

    def action_payslip_payment_report(self, export_format='sepa'):
        action = super().action_payslip_payment_report()
        default_export_format = None
        if self.company_id.country_code == 'CH':
            default_export_format = 'iso20022_ch'
        elif self.company_id.currency_id.name == 'EUR':
            default_export_format = export_format

        if default_export_format:
            action.update({
                'context': {
                    **action['context'],
                    'default_export_format': default_export_format,
                },
            })
        return action
