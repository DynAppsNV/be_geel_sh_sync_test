import json
import logging
from ast import literal_eval
from urllib.parse import urljoin

import requests
import sqlparse

from odoo import fields, models, service
from odoo.tools import json_default, str2bool

_logger = logging.getLogger(__name__)
DATA_SCHEMA_VERSION = "1.0"
ANALYTICS_TIMEOUT = 60  # seconds
ALLOWED_QUERY_TYPES = ["SELECT"]


class DynappsAnalytics(models.TransientModel):  # pylint: disable=no-wizard-in-models
    _name = "xx.dynapps.analytics"
    _description = "Dynapps Analytics"

    name = fields.Char(default="Dynapps Analytics")
    formatted_json_data = fields.Text(compute="_compute_json_data", compute_sudo=True)

    def _compute_json_data(self):
        for rec in self:
            rec.formatted_json_data = json.dumps(
                self._prepare_analytic_data(), indent=4, default=json_default
            )

    def _cron_publish_analytics(self):
        endpoint = self.env["ir.config_parameter"].get_param("dynapps_analytic_endpoint")

        if endpoint and str2bool(endpoint, default=True):
            data = self._prepare_analytic_data()

            requests.post(endpoint, json=data, timeout=ANALYTICS_TIMEOUT)

    def _prepare_analytic_data(self):
        self_lang = self.with_context(lang="en_US")
        get_param = self_lang.env["ir.config_parameter"].get_param
        all_modules = self_lang.env["ir.module.module"].search([])  # pylint: disable=no-search-all
        version_info = service.common.exp_version()
        endpoint = self.env["ir.config_parameter"].sudo().get_param("dynapps_analytic_endpoint")

        data = {
            "data_schema_version": DATA_SCHEMA_VERSION,
            "create_timestamp": fields.Datetime.now().isoformat(),
            "database_name": self_lang.env.cr.dbname,
            "database_uuid": get_param("database.uuid", None),
            "database_expiration": get_param("database.expiration_date", None),
            "internal_users": self_lang.env["res.users"].search_count([("share", "=", False)]),
            "public_users": self_lang.env["res.users"].search_count([("share", "=", True)]),
            "odoo_version": version_info.get("server_serie"),
            "company_count": self_lang.env["res.company"].search_count([]),
            "web_base_url": get_param("web.base.url", None),
            "modules": {},
        }

        for module in all_modules:
            module_data = {
                "state": module.state,
                "author": module.author if module.author is not False else None,
                "installed_version": module.latest_version,
                "disk_version": module.installed_version,
                "dependencies": module.dependencies_id.mapped("name"),
                "shortdesc": module.shortdesc if module.shortdesc is not False else None,
                "website": module.website if module.website is not False else None,
                "category": module.category_id.name,
            }
            data["modules"][module.name] = module_data

        if literal_eval(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("dynapps_analytic_fetch_details", "False")
        ):
            try:
                data_to_fetch = requests.post(
                    urljoin(endpoint + "/", "get_data_to_fetch"),
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                    json={
                        "database_uuid": get_param("database.uuid", None),
                        "odoo_version": version_info.get("server_serie"),
                    },
                    timeout=ANALYTICS_TIMEOUT,
                )
                data_to_fetch.raise_for_status()

                if data_to_fetch.json()["result"]:
                    data["detailed_statistics"] = {}

                    for module, analytic_data in data_to_fetch.json()["result"].items():
                        if (
                            module in data["modules"]
                            and data["modules"][module]["state"] == "installed"
                        ):
                            for rec in analytic_data:
                                parsed_query = sqlparse.parse(rec["query"])

                                # Ensure the query is not a destructive statement
                                if (
                                    parsed_query
                                    and parsed_query[0].get_type() not in ALLOWED_QUERY_TYPES
                                ):
                                    data["detailed_statistics"][rec["report_as"]] = (
                                        "Skipped because of bad query type"
                                    )
                                    continue

                                try:
                                    with self.env.cr.savepoint():
                                        self.env.cr.execute(rec["query"])
                                        data["detailed_statistics"].update(
                                            {
                                                rec["report_as"]: json.loads(
                                                    json.dumps(
                                                        self.env.cr.dictfetchall(),
                                                        default=json_default,
                                                    )
                                                )
                                            }
                                        )
                                except Exception as e:
                                    data["detailed_statistics"][rec["report_as"]] = str(e)
            except Exception as e:
                _logger.exception(e)
            self.env["ir.config_parameter"].sudo().set_param(
                "dynapps_analytic_fetch_details", "False"
            )
        return data

    def action_open_view(self):
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "dyn_analytics.action_dynapps_analytics_form"
        )
        analytic_id = self.sudo().create({})
        action["res_id"] = analytic_id.id

        return action
