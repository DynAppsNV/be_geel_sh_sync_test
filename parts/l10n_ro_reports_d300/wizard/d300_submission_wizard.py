from odoo import models


class L10nRoD300SubmissionWizard(models.TransientModel):
    _name = "l10n_ro.d300.submission.wizard"
    _inherit = "account.return.submission.wizard"
    _description = "Romania D300 Submission Wizard"

    def print_xml(self):
        xml_file = self.return_id.attachment_ids.filtered(lambda a: a.mimetype == 'application/xml')
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{xml_file.id}?download=true",
            "target": "download",
        }
