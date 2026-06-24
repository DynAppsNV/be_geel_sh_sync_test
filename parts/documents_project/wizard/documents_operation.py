from odoo import models


class DocumentsOperation(models.TransientModel):
    _inherit = 'documents.operation'

    def _post_operation_add_hook(self, document):
        if self.attachment_id.res_model == 'project.task' and self.attachment_id.res_id:
            task_record = self.env['project.task'].browse(self.attachment_id.res_id)
            msg_body = self.env._(
                "This document belongs to %(task)s.",
                task=task_record._get_html_link(title=task_record.display_name),
            )
            document.message_post(body=msg_body)
