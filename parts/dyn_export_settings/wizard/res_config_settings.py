import logging

import lxml.etree as etree

from odoo import api, fields, models
from odoo.tools import config

from odoo.addons.module_change_auto_install.patch import _get_modules_auto_install_disabled_dict

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = ["res.config.settings", "dyn.export.settings.mixin"]
    _name = "res.config.settings"

    xx_base_module_name = fields.Char(string="Base Module Name")

    @api.model
    def get_values(self):
        res = super().get_values()
        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        res.update(
            xx_base_module_name=IrConfigParameter.get_param(
                "dyn_export_settings.base_module_name", default="xx_base"
            ),
        )
        return res

    def set_values(self):
        res = super().set_values()
        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        if (
            IrConfigParameter.get_param("dyn_export_settings.base_module_name")
            != self.xx_base_module_name
        ):
            IrConfigParameter.set_param(
                "dyn_export_settings.base_module_name", self.xx_base_module_name
            )
        return res

    def _register_hook(self):
        res = super()._register_hook()
        self._module_change_auto_install()
        return res

    @api.model
    def _module_change_auto_install(self):
        # Uninstall unnecessary modules
        modules2uninstall = self.env["ir.module.module"]
        for module_auto_install_disabled in _get_modules_auto_install_disabled_dict():
            module2uninstall = self.env.ref(
                f"base.module_{module_auto_install_disabled}", raise_if_not_found=False
            )
            if module2uninstall:
                modules2uninstall += module2uninstall
            else:
                _logger.warning(
                    f"_module_change_auto_install: "
                    f"Module '{module_auto_install_disabled}' not found in the database"
                )
        installed_modules = (
            modules2uninstall.filtered(lambda m: m.state == "installed")
            if not config["test_enable"]
            else modules2uninstall
        )
        if installed_modules:
            _logger.info("Uninstalling module(s) " + ", ".join(installed_modules.mapped("name")))
            self.env.cr.execute(
                "UPDATE ir_module_module SET state = %s WHERE name in %s",
                (
                    "to remove",
                    tuple(installed_modules.mapped("name")),
                ),
            )

    @staticmethod
    def _dyn_export_get_export_order():
        return 2

    def _dyn_export_add_xml_id_at_create(self, overwrite=False):
        return False

    def _dyn_export_fields_to_ignore(self):
        return super()._dyn_export_fields_to_ignore() + [
            "company_id",
            "chart_template",
            "po_order_approval",
            "profiling_enabled_until",
            "website_id",
            # Fields from module auth_oauth
            "server_uri_google",
            # Fields from module point_of_sale
            "pos_available_pricelist_ids",
            "pos_iface_available_categ_ids",
            "pos_iface_start_categ_id",
            # TODO: Following fields should be moved to dyn_export_settings_website
            "shared_user_account",
        ]

    def _dyn_export_ignore_field(self, field_name):
        if field_name.startswith("module_"):
            return True
        return super()._dyn_export_ignore_field(field_name)

    def _dyn_export_get_domain(self):
        return [("company_id", "=", self.env.ref("base.main_company").id)]

    def _dyn_export_get_tech(self):
        odoo_settings = self._dyn_export_get_records(order="id desc", limit=1)
        root = self._dyn_export_get_root_xml()
        function_create = etree.SubElement(
            root, "function", attrib={"model": "res.config.settings", "name": "create"}
        )
        _settings = ",\n".join(
            [
                self._dyn_export_translate_setting(k, v, self._name)
                for k, v in sorted(odoo_settings._dyn_export_get_settings().items())
                if odoo_settings._dyn_export_setting_valid_for_export(self._fields[k])
            ]
        )
        result = None
        if _settings:
            eval_string = (
                f"dict(obj().default_get(list(obj().fields_get())),\n**{{\n{_settings},\n}})"
            )
            value_create_str = f"""<value
                model="res.config.settings"
                eval="{eval_string}"
            />"""
            placeholder = etree.Element("placeholder")
            function_create.append(placeholder)
            function_execute = etree.SubElement(
                root, "function", attrib={"model": "res.config.settings", "name": "execute"}
            )
            etree.SubElement(
                function_execute,
                "value",
                attrib={
                    "model": "res.config.settings",
                    "eval": "obj().search([], order='id desc', limit=1).id",
                },
            )
            result = self.env["dyn.export.settings.mixin"]._dyn_export_parse_xml(
                root, value_create_str
            )
        return result

    def _dyn_export_get_module_info(self):  # noqa: C901
        settings_obj = self.env["res.config.settings"]
        installed_modules = []
        disabled_modules = []
        odoo_settings = settings_obj.search(
            [("company_id", "=", self.env.company.id)], order="id desc", limit=1
        )
        for field in odoo_settings.fields_get():
            if field.startswith("module_"):
                module_name = field.removeprefix("module_")
                autoinstall_module = (
                    self.env["ir.module.module"]
                    .search([("name", "=", module_name)])
                    .filtered(lambda m: m.auto_install)
                )
                if odoo_settings[field]:
                    installed_modules.append(module_name)
                elif not odoo_settings[field] and autoinstall_module:
                    if (
                        autoinstall_module.state != "installed"
                        or autoinstall_module.dependencies_id.depend_id.filtered(
                            lambda m: m.state != "installed"
                        )
                    ):
                        disabled_modules.append(module_name)
                elif module_name in _get_modules_auto_install_disabled_dict().keys():
                    disabled_modules.append(module_name)
        return sorted(list(set(installed_modules))), sorted(list(set(disabled_modules)))

    @staticmethod
    def _dyn_export_find_parent_with_tag(node, tag):
        parent_node = node
        while parent_node is not None:
            if parent_node.tag == tag:
                return parent_node
            parent_node = parent_node.getparent()
        return None

    def _dyn_export_get_func(self):
        odoo_settings = self._dyn_export_get_records(order="id desc", limit=1)
        dict_settings = {}
        arch, view = self.env["res.config.settings"]._get_view()
        for k, v in odoo_settings._dyn_export_get_settings().items():
            node = arch.find(f".//field[@name='{k}']...")
            app_node = self._dyn_export_find_parent_with_tag(node, "app")
            if app_node is not None:
                dict_settings.setdefault(app_node.get("string"), [])
                dict_settings[app_node.get("string")].append(
                    {
                        "setting": self._dyn_export_translate_setting(
                            k, v, self._name, use_func_descr=True
                        ),
                    }
                )
            else:
                dict_settings.setdefault("Undefined", [])
                dict_settings["Undefined"].append(
                    {
                        "setting": self._dyn_export_translate_setting(
                            k, v, self._name, use_func_descr=True
                        ),
                    }
                )
        # Sort dictionary by keys and then sort the list values within each key
        # Sort the list of dictionaries by 'breadcrumb' and then by 'setting'
        sorted_data = {}
        for key in sorted(dict_settings.keys()):  # Sort dictionary keys
            value = dict_settings[
                key
            ]  # Sort by breadcrumb first and then by setting within the same breadcrumb group
            sorted_data[key] = sorted(value, key=lambda x: (x["setting"]))
        # Convert to string format
        sorted_data_str = ""
        for key, value in sorted_data.items():
            sorted_data_str += f"{key}:\n"
            for item in value:
                sorted_data_str += f"  - {item['setting']}\n"
            sorted_data_str = sorted_data_str.rstrip("\n") + "\n\n"
        return sorted_data_str.rstrip("\n")
