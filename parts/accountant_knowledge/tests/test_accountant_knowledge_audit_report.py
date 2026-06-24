from lxml import etree

from odoo import Command
from odoo.tests.common import users

from odoo.addons.accountant_knowledge.controller.main import is_html_element_empty
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


class TestAccountantKnowledgeAuditReport(TransactionCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invoice_user = mail_new_test_user(
            cls.env,
            login='invoice_user',
            groups='account.group_account_invoice',
            notification_type='inbox',
        )

    def test_automatically_invite_responsible_users_on_root_article(self):
        """ Check that the responsible users are automatically invited to the
            article linked to the audit report. """

        audit_report = self.env['audit.report'].create({
            'title': 'My Annual Report',
            'responsible_user_ids': [
                Command.link(self.user_demo.id)
            ],
        })

        article = audit_report.knowledge_article_id
        self.assertEqual(len(article.article_member_ids), 2)
        self.assertEqual(article.article_member_ids[0].partner_id, self.env.user.partner_id)
        self.assertEqual(article.article_member_ids[0].permission, 'write')
        self.assertEqual(article.article_member_ids[1].partner_id, self.user_demo.partner_id)
        self.assertEqual(article.article_member_ids[1].permission, 'write')

    @users('invoice_user')
    def test_invoice_user_can_apply_regular_knowledge_template(self):
        """Applying a regular Knowledge template should not require access to accountant-only models."""
        self.assertFalse(self.env['audit.report'].has_access('read'))
        article = self.env['knowledge.article'].create({'name': 'Test Article'})
        # The created article has an empty audit_report_id cached. Clear it to
        # reproduce the uncached access done when loading a template from the UI.
        article.invalidate_recordset(['audit_report_id'])

        body = article.apply_template(
            self.env.ref('knowledge.knowledge_article_template_meeting_minutes').id,
            skip_body_update=True,
        )
        self.assertTrue(body)

    def test_is_html_element_empty(self):
        """ Check that the `is_html_element_empty` method correctly identifies
            empty HTML elements, ignoring all empty tags and whitespace
            characters."""
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div></div>
        ''')))
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div>   </div>
        ''')))
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div><div></div></div>
        ''')))
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div><div> </div></div>
        ''')))
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div><div> </div> </div>
        ''')))
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div> <div> </div> </div>
        ''')))
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div><p><br/></p></div>
        ''')))
        # NBSP character (\u00A0):
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div><p>&#160;<br/></p></div>
        ''')))

        self.assertFalse(is_html_element_empty(etree.fromstring('''
            <div>Hello</div>
        ''')))
        self.assertFalse(is_html_element_empty(etree.fromstring('''
            <div><p>Hello<br/></p></div>
        ''')))
