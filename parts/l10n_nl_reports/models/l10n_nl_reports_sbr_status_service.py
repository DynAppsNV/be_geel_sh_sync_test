import base64
from datetime import timedelta
from tempfile import NamedTemporaryFile

from markupsafe import Markup
from requests.exceptions import ConnectionError

from odoo import _, fields, models
from odoo.addons.l10n_nl_reports.wizard.l10n_nl_reports_sbr_tax_report_wizard import (
    SoapClientWrapper,
)
from odoo.tools.zeep.exceptions import Fault


class L10n_Nl_ReportsSbrStatusService(models.Model):
    _name = 'l10n_nl_reports.sbr.status.service'
    _description = 'Status checking service for Digipoort submission'

    kenmerk = fields.Char('Message Exchange ID')
    company_id = fields.Many2one('res.company', 'Company')
    report_name = fields.Char('Name of the submitted report')
    is_done = fields.Boolean('Is the cycle finished?', default=False)
    closing_entry_id = fields.Many2one('account.move', string='Related closing entry')
    is_test = fields.Boolean('Is it a test?')

    def _cron_process_submission_status(self):
        ongoing_processes = self.search([('is_done', '=', False)])
        if not ongoing_processes:
            return
        serv_root_cert = ongoing_processes[0].company_id._l10n_nl_get_server_root_certificate_bytes()   # The root certificate is the same for all processes
        with NamedTemporaryFile() as f:
            f.write(serv_root_cert)
            f.flush()

            ongoing_processes_responses = {}
            for process in ongoing_processes:
                cert_sudo = process.company_id.l10n_nl_reports_sbr_cert_id.sudo()
                cer_pem = base64.b64decode(cert_sudo.pem_certificate)
                key_pem = base64.b64decode(cert_sudo.private_key_id.pem_key)
                wsdl = 'https://' + ('preprod-' if process.is_test else '') + 'dgp2.procesinfrastructuur.nl/wus/2.0/statusinformatieservice/1.2?wsdl'
                service_address = 'https://' + ('wus.preproductie.digipoort.' if process.is_test else 'wus.digipoort.') + 'logius.nl/wus/2.0/statusinformatieservice/1.2'

                try:
                    _client, service = SoapClientWrapper().create_soap_client_logius(wsdl, f, cer_pem, key_pem, serv_root_cert, service_address)
                    ongoing_processes_responses[process] = service.getStatussenProces(
                        kenmerk=process.kenmerk,
                        autorisatieAdres='http://geenausp.nl',
                    )
                except Fault as fault:
                    detail_fault = fault.detail.getchildren()[0]
                    error_description = detail_fault.find("fault:foutbeschrijving", namespaces={**fault.detail.nsmap, **detail_fault.nsmap}).text
                    process.is_done = True
                    if not process.is_test:
                        subject = _("%(report_name)s status retrieval failed", report_name=process.report_name)
                        body = _(
                            "The status retrieval for the %(report_name)s with discussion ID '%(id)s' failed with the error:%(newline)s%(newline)s"
                            "%(italic_start)s%(error)s%(italic_end)s%(newline)s%(newline)s"
                            "Try submitting your report again.",
                            report_name=process.report_name,
                            id=process.kenmerk,
                            error=error_description,
                            newline=Markup("<br>"),
                            italic_start=Markup("<i>"),
                            italic_end=Markup("</i>"),
                        )
                        process._process_messages_and_statuses(process.closing_entry_id.closing_return_id, subject, body, status='error')
                except ConnectionError:
                    # In case the server or the connection is not accessible at the moment,
                    # we'll just skip this process and trigger a new cron for later
                    pass

        for process, response in ongoing_processes_responses.items():
            for status in response:
                account_return = process.closing_entry_id.closing_return_id
                if status.statusFoutcode:
                    process.is_done = True
                    ongoing_processes -= process
                    if not process.is_test:
                        subject = _("%(report_name)s submission failed", report_name=process.report_name)
                        body = _(
                            "The submission for the %(report_name)s with discussion ID '%(id)s' failed with the error:%(newline)s%(newline)s"
                            "%(italic_start)s%(error)s%(italic_end)s%(newline)s"
                            "%(italic_start)s%(detailed_error)s%(italic_end)s%(newline)s%(newline)s"
                            "Try submitting your report again.",
                            report_name=process.report_name,
                            id=process.kenmerk,
                            error=status.statusomschrijving,
                            detailed_error=status.statusFoutcode.foutbeschrijving,
                            newline=Markup("<br>"),
                            italic_start=Markup("<i>"),
                            italic_end=Markup("</i>"),
                        )
                        process._process_messages_and_statuses(account_return, subject, body, status='error')
                    break
                if status.statuscode == '500':
                    # See "Statussenflow - Aanleverproces Belastingdienst": https://www.logius.nl/domeinen/publieke-diensten/digipoort
                    process.is_done = True
                    ongoing_processes -= process
                    if not process.is_test:
                        subject = _("%(report_name)s submission succeeded", report_name=process.report_name)
                        body = _(
                            "The submission for the %(report_name)s with discussion ID '%(id)s' was successfully received by Digipoort.",
                            report_name=process.report_name,
                            id=process.kenmerk,
                        )
                        process._process_messages_and_statuses(account_return, subject, body, status='accepted')
                    break

        if ongoing_processes:
            # If there are still unfinished processes, we trigger a cron to check the status again in one minute
            statusinformatieservice_cron = self.env.ref('l10n_nl_reports.cron_l10n_nl_reports_status_process')
            statusinformatieservice_cron._trigger(fields.Datetime.now() + timedelta(minutes=1))

    def _process_messages_and_statuses(self, account_return, subject, body, attachments=None, subscribe=False, status=None):
        account_return.message_post(
            subject=subject,
            body=body,
            author_id=self.env.ref('base.partner_root').id,
            subtype_id=self.env.ref('mail.mt_comment').id,
            attachments=attachments or [],
        )
        if subscribe:
            account_return.message_subscribe(partner_ids=[self.env.user.partner_id.id])
