The module enables you to export the account configuration of the Odoo instance.

Following extra features are provided by the module:
 - Added audit rules on following model

   - Taxes (account.tax)
   - Fiscal Positions (account.fiscal.position)
   - Journals (account.journal)
   - Payment Terms (account.payment.term)
   - Follow-up levels (account_followup.followup.line)
 - It should not be possible to remove account.account records with external ID prefix "account.".
 - Enable archiving on account.account model.

   - The record will also be marked as deprecated.
