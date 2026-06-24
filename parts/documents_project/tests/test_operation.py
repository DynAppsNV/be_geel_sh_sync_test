from odoo.addons.documents.tests.test_documents_common import TransactionCaseDocuments
from odoo.tests.common import RecordCapturer


class TestDocumentsOperations(TransactionCaseDocuments):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.task = (
            cls.env['project.task']
            .with_context(mail_create_nolog=True)
            .create(
                {
                    'name': "Pigs UserTask",
                    'user_ids': cls.doc_user,
                }
            )
        )
        cls.attachment = cls.env['ir.attachment'].create(
            {
                'name': "einvoice_a.json",
                'res_model': 'project.task',
                'res_id': cls.task.id,
                'raw': b'{"Irn": "1234567890"}',
            }
        )

    def test_add_document_operation_on_task(self):
        operation = self.env['documents.operation'].create(
            {
                'destination': str(self.folder_a.id),
                'operation': 'add',
                'attachment_id': self.attachment.id,
            }
        )

        with RecordCapturer(self.env['documents.document']) as document_capturer:
            operation.action_confirm()
        created_documents = document_capturer.records

        self.assertEqual(len(created_documents), 1)
        creation_message = self.env['mail.message'].search(
            [
                ('res_id', '=', created_documents[0].id),
                ('body', 'ilike', "This document belongs to"),
            ]
        )
        self.assertTrue(creation_message)
