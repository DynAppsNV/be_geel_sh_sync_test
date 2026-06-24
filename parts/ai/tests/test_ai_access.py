# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import new_test_user, TransactionCase, tagged, users


@tagged('post_install', '-at_install')
class TestAiFieldsAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal_user = new_test_user(cls.env, 'internal')

    def test_ai_access_agent_system(self):
        # system: every right
        agent = self.env['ai.agent'].create({'name': 'test agent'})
        agent.write({'subtitle': 'bloups'})
        self.assertEqual(self.env['ai.agent'].search([('name', '=', 'test agent')]), agent)
        agent.unlink()
        self.assertFalse(agent.exists())

    @users('internal')
    def test_ai_access_agent_internal(self):
        # internal: readonly
        with self.assertRaises(AccessError):
            self.env['ai.agent'].create({'name': 'test agent'})
        agent_sudo = self.env['ai.agent'].sudo().create({'name': 'test agent'})
        agent = self.env['ai.agent'].search([('name', '=', 'test agent')])
        self.assertEqual(agent, agent_sudo)
        self.assertEqual('test agent', agent.name)
        with self.assertRaises(AccessError):
            agent.write({'subtitle': 'bloups'})
        with self.assertRaises(AccessError):
            agent.unlink()

    def test_ai_access_embedding_system(self):
        # system: every right
        attachment = self.env['ir.attachment'].create({
            'name': 'test attachment',
            'datas': 'dGVzdA==',  # "test" in base64
            'res_model': 'ai.embedding',
            'res_id': 0,
        })
        embedding = self.env['ai.embedding'].create({
            'attachment_id': attachment.id,
            'content': 'test content',
            'embedding_model': 'text-embedding-3-small',
        })
        embedding.write({'content': 'updated content'})
        self.assertEqual(
            self.env['ai.embedding'].search([('id', '=', embedding.id)]),
            embedding
        )
        embedding.unlink()
        self.assertFalse(embedding.exists())

    @users('internal')
    def test_ai_access_embedding_internal(self):
        # internal: readonly
        attachment = self.env['ir.attachment'].create({
            'name': 'test attachment',
            'datas': 'dGVzdA==',  # "test" in base64
            'res_model': 'ai.embedding',
            'res_id': 0,
        })
        with self.assertRaises(AccessError):
            self.env['ai.embedding'].create({
                'attachment_id': attachment.id,
                'content': 'test content',
                'embedding_model': 'text-embedding-3-small',
            })
        embedding_sudo = self.env['ai.embedding'].sudo().create({
            'attachment_id': attachment.id,
            'content': 'test content',
            'embedding_model': 'text-embedding-3-small',
        })
        embedding = self.env['ai.embedding'].search([('id', '=', embedding_sudo.id)])
        self.assertEqual(embedding, embedding_sudo)
        self.assertEqual('test content', embedding.content)
        with self.assertRaises(AccessError):
            embedding.write({'content': 'updated content'})
        with self.assertRaises(AccessError):
            embedding.unlink()

    def test_ai_access_topic_system(self):
        # system: every right
        topic = self.env['ai.topic'].create({
            'name': 'test topic',
            'description': 'topic description',
        })
        topic.write({'description': 'updated topic description'})
        self.assertEqual(
            self.env['ai.topic'].search([('id', '=', topic.id)]),
            topic
        )
        topic.unlink()
        self.assertFalse(topic.exists())

    @users('internal')
    def test_ai_access_topic_internal(self):
        # internal: readonly
        with self.assertRaises(AccessError):
            self.env['ai.topic'].create({
                'name': 'test topic',
                'description': 'topic description',
            })
        topic_sudo = self.env['ai.topic'].sudo().create({
            'name': 'test topic',
            'description': 'topic description',
        })
        topic = self.env['ai.topic'].search([('id', '=', topic_sudo.id)])
        self.assertEqual(topic, topic_sudo)
        self.assertEqual('test topic', topic.name)
        with self.assertRaises(AccessError):
            topic.write({'description': 'updated topic description'})
        with self.assertRaises(AccessError):
            topic.unlink()

    @users('internal')
    def test_generate_response_non_admin_tool_access(self):
        """Test that non-admin users can call _generate_response without access errors on tool_ids."""

        tool = self.env['ir.actions.server'].sudo().create({
            'name': 'Test Tool',
            'state': 'code',
            'model_id': self.env.ref('base.model_res_partner').id,
            'code': "",
            'use_in_ai': True,
        })

        topic = self.env['ai.topic'].sudo().create({
            'name': 'Test Topic',
            'tool_ids': [Command.set([tool.id])],
        })

        agent = self.env['ai.agent'].sudo().create({
            'name': 'Test Agent',
            'topic_ids': [Command.set([topic.id])],
        })

        with patch('odoo.addons.ai.utils.llm_api_service.LLMApiService.request_llm') as mock_request_llm:
            mock_request_llm.return_value = ['Hello!']

            response = agent.with_user(self.env.user)._generate_response("hello")

            self.assertEqual(response, ['Hello!'])
            mock_request_llm.assert_called_once()
            call_kwargs = mock_request_llm.call_args.kwargs
            self.assertIn('tools', call_kwargs)
            self.assertEqual(len(call_kwargs['tools']), 1)
            self.assertEqual('Test Tool', next(iter(call_kwargs['tools'].values()))[0])
