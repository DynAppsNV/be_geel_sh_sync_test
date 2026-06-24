from odoo import models


class AccountReturn(models.Model):
    _inherit = 'account.return'

    def _generate_locking_attachments(self, options):
        # Extends account_reports
        super()._generate_locking_attachments(options)
        if self.type_external_id == 'l10n_sk_reports.sk_tax_return_type':
            self._add_attachment(self.type_id.report_id.dispatch_report_action(options, 'export_to_xml'))
