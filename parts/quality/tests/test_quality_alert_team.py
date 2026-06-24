# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestQualityAlertTeam(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = cls.env['quality.alert.team'].create({
            'name': 'Mail Team',
            'alias_name': 'mail-team',
        })
        cls.another_company = cls.env['res.company'].create({'name': 'Another Company'})

    def test_quality_alert_team_company_consistency(self):
        self.assertTrue(self.team.company_id)
        self.assertRegex(self.team.alias_defaults, f'[\'"]company_id[\'"]: {self.team.company_id.id}')
        with self.assertRaises(ValidationError):
            self.team.company_id = False
        self.team.company_id = self.another_company
        self.assertRegex(self.team.alias_defaults, f'[\'"]company_id[\'"]: {self.another_company.id}')
