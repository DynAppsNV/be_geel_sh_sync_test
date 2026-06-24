from odoo import api, fields, models


class Website(models.Model):
    _name = "website"
    _inherit = ["website", "server.env.mixin"]
    _server_env_section_name_field = "code"

    code = fields.Char(
        string="Environment settings identifier",
        help="Technical identifier used as mapping to enforce and maintain "
        "certain website settings from the server environment config",
    )
    domain = fields.Char(
        search="_search_website_domain",
        help="This field is being managed by server environment config and cannot be overwritten"
        " manually when the environment settings identifier field is set",
    )
    name = fields.Char(
        search="_search_website_name",
        help="This field is being managed by server environment settings and cannot be overwritten"
        " manually when the environment settings identifier field is set",
    )

    @api.model
    def _search_website_domain(self, oper, value):
        """Keep the domain field searchable to allow domain in search view."""
        websites = self.search_fetch([], ["domain"]).filtered_domain([("domain", oper, value)])
        return fields.Domain([("id", "in", websites.ids)])

    @api.model
    def _search_website_name(self, oper, value):
        """Keep the name field searchable to allow name in search view."""
        websites = self.search_fetch([], ["name"]).filtered_domain([("name", oper, value)])
        return fields.Domain([("id", "in", websites.ids)])

    @property
    def _server_env_fields(self):
        base_fields = super()._server_env_fields
        website_fields = {
            "name": {},
            "domain": {},
        }
        base_fields.update(website_fields)
        return base_fields

    @api.model
    def _server_env_global_section_name(self):
        """Name of the global section in the configuration files"""
        return "website"
