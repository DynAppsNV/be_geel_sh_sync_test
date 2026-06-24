from odoo.tests import tagged

from odoo.addons.server_environment.tests.common import ServerEnvironmentCase


@tagged("post_install", "-at_install")
class TestCompanyEnvironment(ServerEnvironmentCase):
    def test_website(self):
        website = self.env["website"].search([("name", "=", "My Custom Website")])
        self.assertTrue(website)
        self.assertEqual(website.domain, "http://localhost:8069")
