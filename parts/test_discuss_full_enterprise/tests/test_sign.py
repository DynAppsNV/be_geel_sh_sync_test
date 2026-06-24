from odoo.tests import HttpCase, tagged
from odoo import Command


@tagged('-at_install', 'post_install')
class TestSignUI(HttpCase):

    def test_sign_cog_button(self):
        project = self.env['project.project'].create({
            'name': 'Test Sign Project',
            'type_ids': [Command.create({'name': 'To Do'})],
        })
        self.env['project.task'].create({
            'name': 'Test Sign Task',
            'project_id': project.id,
        })
        self.start_tour("/odoo", "test_sign_ui_tour", login="admin")
