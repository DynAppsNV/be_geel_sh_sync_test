from odoo.addons.server_environment.tests.common import ServerEnvironmentCase

website_config = """
[website]
domain = localhost

[website.W1]
domain = https://www.mywebsite1.com

[website.W2]
domain = https://www.mywebsite2.com
"""


class TestWebsiteEnvironment(ServerEnvironmentCase):
    def setUp(self):
        super().setUp()
        self.website1 = self.env["website"].create({"name": "Website1", "code": "W1"})
        self.website2 = self.env["website"].create({"name": "Website2", "code": "W2"})
        self.website3 = self.env["website"].create({"name": "Website3"})

    def test_website_settings(self):
        with self.load_config(public=website_config):
            self.assertEqual(self.website1.domain, "https://www.mywebsite1.com")
            self.assertEqual(self.website2.domain, "https://www.mywebsite2.com")
            self.assertEqual(self.website3.domain, "localhost")

    def test_search_website(self):
        self.assertIsNotNone(
            self.env["website"].search([("domain", "=", "https://www.mywebsite1.com")])
        )
        self.assertIsNotNone(
            self.env["website"].search([("domain", "!=", "https://www.mywebsite3.com")])
        )
        self.assertIsNotNone(self.env["website"].search([("domain", "ilike", "mywebsite1")]))
        self.assertIsNotNone(self.env["website"].search([("domain", "not like", "mywebsite3")]))
        self.assertIsNotNone(self.env["website"].search([("name", "=", "Website3")]))
        self.assertIsNotNone(self.env["website"].search([("name", "=", "Website1")]))
