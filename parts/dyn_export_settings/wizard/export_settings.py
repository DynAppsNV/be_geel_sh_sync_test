import json
import os

import yaml

from odoo import fields, models
from odoo.tools import file_path

from odoo.addons.module_change_auto_install.patch import _get_modules_auto_install_disabled_dict


class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)


class DynappsExportSettings(models.TransientModel):
    _name = "xx.dynapps.export.settings"
    _description = "Dynapps Export Settings"

    name = fields.Char(default="Export Settings")
    languages_func = fields.Text(compute="_compute_settings")
    settings_func = fields.Text(compute="_compute_settings")
    installed_modules_tech = fields.Text(compute="_compute_settings")
    installed_modules_func = fields.Text(compute="_compute_settings")
    installed_modules_settings_func = fields.Text(compute="_compute_settings")
    installed_modules_diff = fields.Text(compute="_compute_settings")
    disabled_modules_tech = fields.Text(compute="_compute_settings")
    disabled_modules_func = fields.Text(compute="_compute_settings")
    disabled_modules_settings_func = fields.Text(compute="_compute_settings")
    disabled_modules_diff = fields.Text(compute="_compute_settings")
    company_settings_func = fields.Text(compute="_compute_settings")
    partner_logo_ids = fields.One2many(
        comodel_name="xx.partner.logo", compute="_compute_partner_logos", inverse_name="settings_id"
    )
    custom_field_ids = fields.One2many(
        comodel_name="xx.module.custom.fields",
        compute="_compute_custom_fields",
        inverse_name="settings_id",
        string="Custom Fields",
    )
    module_data_ids = fields.One2many(
        comodel_name="xx.module.data",
        compute="_compute_module_data",
        inverse_name="settings_id",
        string="Module Data",
    )

    def _compute_custom_fields(self):
        base_module = self.env["dyn.export.settings.mixin"]._dyn_export_get_base_module()
        for rec in self:
            rec.custom_field_ids.sudo().unlink()
            values = []
            custom_modules = base_module.downstream_dependencies().sorted("name")
            for custom_module in custom_modules:
                # Get all fields that are part of the custom module
                fields_data = self.env["ir.model.data"].search(
                    [("module", "=", custom_module.name), ("model", "=", "ir.model.fields")]
                )
                # Filter out fields that are not part of the custom module which
                # inherits from dyn.export.settings.mixin
                for _model in (
                    self.env["ir.model.fields"]
                    .browse(fields_data.mapped("res_id"))
                    .mapped("model_id")
                    .filtered(
                        lambda r: isinstance(
                            self.env[r.model], self.pool["dyn.export.settings.mixin"]
                        )
                    )
                ).sorted("name"):
                    custom_fields = (
                        self.env["ir.model.fields"]
                        .browse(fields_data.mapped("res_id"))
                        .filtered(
                            lambda r, m=_model, c=custom_module: r.model_id == m
                            and self.env[
                                "dyn.export.settings.mixin"
                            ]._dyn_export_is_defined_in_module(r, m, c)
                            and not self.env[m.model]._dyn_export_ignore_field(r.name)
                        )
                    )
                    if custom_fields:
                        values.append(
                            {
                                "settings_id": rec.id,
                                "model_id": _model.id,
                                "module_id": custom_module.id,
                                "field_ids": custom_fields.ids,
                            }
                        )
            if values:
                rec.custom_field_ids.sudo().create(values)

    def _compute_module_data(self):
        custom_module_names = (
            self.env["dyn.export.settings.mixin"]
            ._dyn_export_get_base_module()
            .downstream_dependencies()
            .mapped("name")
        )
        for rec in self:
            rec.module_data_ids.sudo().unlink()
            values = []
            for module in rec.custom_field_ids.mapped("module_id"):
                for _model in rec.custom_field_ids.filtered(
                    lambda r, m=module: r.module_id == m
                ).mapped("model_id"):
                    values.append(
                        {
                            "settings_id": rec.id,
                            "module_id": module.id,
                            "model_id": _model.id,
                            "data_filename": self.env[_model.model]._dyn_export_get_data_filename(),
                        }
                    )
            # Add the data file for the base module
            base_models = (
                self.env["ir.model"]  # pylint: disable=W8163
                .search([])
                .filtered(
                    lambda r: r.model in self.env
                    and isinstance(self.env[r.model], self.pool["dyn.export.settings.mixin"])
                    and not self.env[r.model]._abstract
                )
            )
            for base_model in base_models:
                in_modules = [m.strip() for m in base_model.modules.split(",")]
                if [m for m in in_modules if m not in custom_module_names]:
                    values.append(
                        {
                            "settings_id": rec.id,
                            "module_id": self.env["dyn.export.settings.mixin"]
                            ._dyn_export_get_base_module()
                            .id,
                            "model_id": base_model.id,
                            "data_filename": self.env[
                                base_model.model
                            ]._dyn_export_get_data_filename(),
                        }
                    )
            if values:
                rec.module_data_ids.sudo().create(values)

    def _compute_partner_logos(self):
        for rec in self:
            rec.partner_logo_ids.sudo().unlink()
            res_field = "image_1920"
            values = []
            for partner in (
                self.env["dyn.export.settings.mixin"]
                ._dyn_export_get_companies()
                .mapped("partner_id")
                .filtered(res_field)
            ):
                filename = partner._dyn_export_get_xml_id().split(".")[-1:][0]
                extension = self.env["dyn.export.settings.mixin"]._get_file_extension(
                    partner, res_field
                )
                values.append(
                    {
                        "settings_id": rec.id,
                        "partner_id": partner.id,
                        "logo": partner.image_1920,
                        "filename": f"{filename}{extension}",
                    }
                )
            if values:
                rec.partner_logo_ids.sudo().create(values)

    def _compute_settings(self):
        self = self.with_context(lang="en_US").with_company(self.env.ref("base.main_company"))
        config_settings_obj = self.env["res.config.settings"]
        config_settings = config_settings_obj.create(
            dict(config_settings_obj.default_get(list(config_settings_obj.fields_get())))
        )
        for rec in self:
            # Calculate the tech and functional data for the installed and disabled modules
            rec.settings_func = config_settings._dyn_export_get_func()
            (
                config_installed_modules,
                config_disabled_modules,
            ) = config_settings._dyn_export_get_module_info()
            installed_modules = self.env[
                "dyn.export.settings.mixin"
            ]._dyn_export_get_installed_modules()
            rec.installed_modules_tech = self._get_installed_modules_tech(
                config_installed_modules + installed_modules
            )
            rec.installed_modules_settings_func = self._get_modules_settings_func(
                config_installed_modules
            )
            rec.installed_modules_func = self._get_modules_func(
                list(set(installed_modules) - set(config_installed_modules))
            )
            rec.installed_modules_diff = self._get_installed_modules_diff()
            rec.disabled_modules_tech = self._get_disabled_modules_tech(
                config_disabled_modules + self._get_auto_disabled_modules()
            )
            rec.disabled_modules_settings_func = self._get_modules_func(config_disabled_modules)
            rec.disabled_modules_func = self._get_modules_func(
                list(set(self._get_auto_disabled_modules()) - set(config_disabled_modules))
            )
            rec.disabled_modules_diff = self._get_disabled_modules_diff()
            rec.company_settings_func = self.env["res.company"]._dyn_export_get_func()
            rec.languages_func = self.env["res.lang"]._dyn_export_get_func()

    def action_open_view(self):
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "dyn_export_settings.action_dynapps_export_settings"
        )
        action["res_id"] = self.sudo().create({}).id
        return action

    def export_settings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/dynapps/settings/download/{self.id}",
            "target": "self",
        }

    @staticmethod
    def _add_data_files(data, data_files_to_add):
        data_files = data
        for data_file_to_add in data_files_to_add:
            if data_file_to_add not in data_files:
                data_files.append(data_file_to_add)
        return data_files

    def get_updated_manifest_data(self, module, data_files):
        self.ensure_one()
        manifest_data = self.env[
            "dyn.export.settings.mixin"
        ]._dyn_export_get_original_manifest_data(module)
        manifest_data["data"] = self._add_data_files(manifest_data.get("data", []), data_files)
        if module == self.env["dyn.export.settings.mixin"]._dyn_export_get_base_module():
            manifest_data["depends"] = json.loads(self.installed_modules_tech)["depends"]
        return manifest_data

    def get_original_build_data(self):
        self.ensure_one()
        try:
            with open(
                os.path.join(
                    os.path.dirname(
                        os.path.dirname(
                            os.path.dirname(
                                file_path(
                                    self.env["dyn.export.settings.mixin"]
                                    ._dyn_export_get_base_module()
                                    .name
                                )
                            )
                        )
                    ),
                    "dyn-build.yaml",
                )
            ) as file:
                build_config = yaml.safe_load(file.read())
        except FileNotFoundError:
            build_config = {}
        # Ensure 'config' and nested keys exist in build_config
        if "config" not in build_config:
            build_config["config"] = {}
        if "odoo" not in build_config["config"]:
            build_config["config"]["odoo"] = {}
        if "module_change_auto_install" not in build_config["config"]["odoo"]:
            build_config["config"]["odoo"]["module_change_auto_install"] = {}
        if "disabled_modules" not in build_config["config"]["odoo"]["module_change_auto_install"]:
            build_config["config"]["odoo"]["module_change_auto_install"]["disabled_modules"] = []
        build_config["config"]["odoo"]["module_change_auto_install"]["enabled"] = True
        return build_config

    def get_updated_build_data(self):
        self.ensure_one()
        build_config = self.get_original_build_data()
        build_config["config"]["odoo"]["module_change_auto_install"]["disabled_modules"] = (
            yaml.safe_load(self.disabled_modules_tech)["config"]["odoo"][
                "module_change_auto_install"
            ]["disabled_modules"]
        )
        return yaml.dump(build_config, Dumper=Dumper, default_flow_style=False)

    def _get_base_data_file_path(self, filename):
        return os.path.join(
            self.env["dyn.export.settings.mixin"]._dyn_export_get_base_module().name,
            "data",
            filename,
        )

    def _get_auto_disabled_modules(self):
        return [
            module.name
            for module in self.env["ir.module.module"]
            .search([("state", "=", "uninstalled"), ("name", "not ilike", "l10n_")])
            .filtered(lambda m: m.auto_install)
            | self.env["ir.module.module"].search(
                [
                    ("state", "=", "uninstalled"),
                    (
                        "name",
                        "in",
                        list(_get_modules_auto_install_disabled_dict().keys()),
                    ),
                ]
            )
            if all([x.state == "installed" for x in module.dependencies_id])
        ]

    @staticmethod
    def _get_list_diff(old_list, new_list):
        # Items added in new_list (not in old_list)
        added = [item for item in new_list if item not in old_list]

        # Items removed from old_list (not in new_list)
        removed = [item for item in old_list if item not in new_list]

        diff = ""
        if added:
            diff += f"Added: {json.dumps(added)}\n"
        if removed:
            diff += f"Removed: {json.dumps(removed)}"
        return diff

    def _get_disabled_modules_diff(self):
        build_data = self.get_original_build_data()
        old_content = build_data["config"]["odoo"]["module_change_auto_install"]["disabled_modules"]
        new_content = yaml.safe_load(self.disabled_modules_tech)["config"]["odoo"][
            "module_change_auto_install"
        ]["disabled_modules"]
        return self._get_list_diff(old_content, new_content)

    def _get_installed_modules_diff(self):
        manifest_data = self.env[
            "dyn.export.settings.mixin"
        ]._dyn_export_get_original_manifest_data(
            self.env["dyn.export.settings.mixin"]._dyn_export_get_base_module()
        )
        old_content = manifest_data.get("depends", [])
        new_content = json.loads(self.installed_modules_tech)["depends"]
        return self._get_list_diff(old_content, new_content)

    def _get_modules_settings_func(self, modules):
        return "\n".join(
            sorted(
                [
                    f"{self.env['res.config.settings']._fields['module_' + m].string} ({m})"
                    for m in modules
                ]
            )
        )

    def _get_modules_func(self, modules):
        _modules = self.env["ir.module.module"].search([("name", "in", modules)])
        return "\n".join(
            sorted(
                [
                    f"{_modules.filtered(lambda r, m=module: r.name == m).shortdesc} ({module})"
                    for module in modules
                ]
            )
        )

    @staticmethod
    def _get_installed_modules_tech(modules):
        return json.dumps({"depends": sorted(list(set(modules)))}, sort_keys=True, indent=4)

    @staticmethod
    def _get_disabled_modules_tech(modules):
        return yaml.dump(
            {
                "config": {
                    "odoo": {
                        "module_change_auto_install": {
                            "disabled_modules": sorted(list(set(modules))),
                            "enabled": True,
                        }
                    }
                }
            },
            Dumper=Dumper,
            sort_keys=True,
        )
