from odoo import models


class L10n_Nl_ReportsSbrStatusService(models.Model):
    _inherit = 'l10n_nl_reports.sbr.status.service'

    def _process_messages_and_statuses(self, account_return, subject, body, attachments=None, subscribe=False, status=None):
        super()._process_messages_and_statuses(account_return, subject, body, attachments, status, subscribe)
        if status:
            account_return.l10n_nl_sbr_status = status
            if status == 'accepted':
                account_return.state = 'submitted'
                account_return._on_post_submission_event()
