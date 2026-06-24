from odoo import models, fields, api


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.avatax.unique.code', 'account.move']

    avatax_tax_date = fields.Date(
        string="Avatax Date",
        help="Avatax will use this date to calculate the tax on this invoice. "
             "If not specified it will use the Invoice Date.",
    )

    @api.depends('fiscal_position_id', 'move_type')
    def _compute_is_tax_computed_externally(self):
        # EXTENDS 'account_external_tax' to enable external taxes on sale documents.
        super()._compute_is_tax_computed_externally()
        for move in self:
            if move.is_avatax:
                move.is_tax_computed_externally = move.is_sale_document()

    def _post(self, soft=True):
        res = super()._post(soft=soft)

        # This recreates the existing transaction with the invoice name as the referenceCode (unknown
        # before posting), and also commits the transaction. This deliberately doesn't pass the output
        # back through _set_external_taxes(), because a posted invoice cannot be modified and the taxes
        # were just calculated before in super()._post() by the account_external_tax module.
        self.filtered(
            lambda move: move.is_avatax and move.is_tax_computed_externally and not move._is_downpayment()
        )._get_external_taxes()

        return res

    def _get_avatax_service_params(self, commit=False):
        # EXTENDS 'account.external.tax.mixin'
        res = super()._get_avatax_service_params(commit)
        document_type = {
            'out_invoice': 'SalesInvoice',
            'out_refund': 'ReturnInvoice',
            'in_invoice': 'PurchaseInvoice',
            'in_refund': 'ReturnInvoice',
            'entry': 'Any',
        }[self.move_type]

        avatax_company = self._find_avatax_credentials_company(self.company_id)
        res.update({
            'is_refund': self.move_type == 'out_refund',
            'document_type': document_type,
            'document_date': self.invoice_date,
            'tax_date': (self.reversed_entry_id.avatax_tax_date or self.reversed_entry_id.invoice_date) if self.reversed_entry_id else self.avatax_tax_date,
            'perform_address_validation': self.fiscal_position_id.is_avatax and self.move_type in ('out_invoice', 'out_refund') and not self.origin_payment_id,
            'commit': self.state == 'posted' and avatax_company and avatax_company.avalara_commit,
        })

        return res
