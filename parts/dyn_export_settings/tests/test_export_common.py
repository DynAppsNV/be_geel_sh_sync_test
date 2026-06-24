from psycopg2._json import Json

import odoo
from odoo import Command, fields
from odoo.fields import Field
from odoo.models import BaseModel
from odoo.tests import common, patch


class TestExportSettingsCommon(common.TransactionCase):
    # Stores definitions for dynamically added xx_ fields so that each
    # _setup_models__ re-run restores the correct definition (not the one
    # from whatever field happens to be in the current _create_field closure).
    _xx_field_definitions: dict = {}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.cr.execute(
            "ALTER TABLE ir_model_fields DROP CONSTRAINT ir_model_fields_name_manual_field"
        )
        cls.base_company = cls.env.ref("dyn_export_settings.base_company")
        cls.test_company = cls.env["res.company"].create({"name": "Test Company"})
        cls.x_studio_field = cls.env["ir.model.fields"].create(
            {
                "model_id": cls.env.ref("base.model_res_partner").id,
                "name": "x_studio_field",
                "field_description": "New Studio Field",
                "ttype": "char",
                "store": True,
            }
        )
        cls.base_module = cls.env["ir.module.module"].create(
            {
                "name": "xx_base",
                "state": "installed",
                "imported": True,
                "dependencies_id": [Command.create({"name": "dyn_export_settings"})],
            }
        )
        cls.xx_new_field_properties_definition = cls._create_field(
            "xx_new_field_properties_definition",
            fields.PropertiesDefinition(string="Properties Definition"),
        )
        cls.env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": "xx_base.xx_new_field_properties_definition",
                    "record": cls.xx_new_field_properties_definition,
                }
            ]
        )
        cls.xx_new_field_properties = cls._create_field(
            "xx_new_field_properties",
            fields.Properties(
                string="Properties", definition="parent_id.xx_new_field_properties_definition"
            ),
        )
        cls.env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": "xx_base.xx_new_field_properties",
                    "record": cls.xx_new_field_properties,
                }
            ]
        )
        cls.env["ir.module.module"].create(
            {
                "name": "xx_base_extra",
                "state": "installed",
                "imported": True,
                "dependencies_id": [Command.create({"name": "xx_base"})],
            }
        )
        cls.xx_new_field = cls._create_field("xx_new_field", fields.Char(string="New Char Field"))
        cls.env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": "xx_base_extra.xx_new_field",
                    "record": cls.xx_new_field,
                }
            ]
        )
        cls.env["ir.module.module"].create(
            {
                "name": "xx_base_extra_html",
                "state": "installed",
                "imported": True,
                "dependencies_id": [Command.create({"name": "xx_base"})],
            }
        )
        cls.xx_new_field_html = cls._create_field(
            "xx_new_field_html", fields.Html(string="New HTML Field", translate=True)
        )
        cls.env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": "xx_base_extra_html.xx_new_field_html",
                    "record": cls.xx_new_field_html,
                }
            ]
        )
        cls.base_company.partner_id._write(
            {
                "xx_new_field_html": Json(
                    {
                        "en_US": "<p>English</p>",
                        "nl_BE": "<p>Dutch</p>",
                    }
                )
            }
        )
        cls.env["ir.module.module"].create(
            {
                "name": "xx_base_extra_date",
                "state": "installed",
                "imported": True,
                "dependencies_id": [Command.create({"name": "xx_base"})],
            }
        )
        cls.xx_new_field_date = cls._create_field(
            "xx_new_field_date", fields.Date(string="New Date Field")
        )
        cls.env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": "xx_base_extra_date.xx_new_field_date",
                    "record": cls.xx_new_field_date,
                }
            ]
        )
        cls.env["ir.module.module"].create(
            {
                "name": "xx_base_no_fields",
                "state": "installed",
                "imported": True,
                "dependencies_id": [Command.create({"name": "xx_base"})],
            }
        )

        cls.env["ir.config_parameter"].sudo().set_param(
            "dyn_export_settings.base_module_name", "xx_base"
        )
        cls.wizard = cls.env["xx.dynapps.export.settings"].create({})
        cls.wizard._compute_module_data()

    @classmethod
    def _create_field(cls, name, field, model=None):
        model = model or cls.env.ref("base.model_res_partner")
        orig_add_field = odoo.orm.model_classes.add_field

        # Register this field's definition so subsequent _setup_models__ calls
        # (triggered by later ir.model.fields.create()) restore the correct value.
        cls._xx_field_definitions[name] = field._args__.get("definition", None)

        def add_field(model_cls: type[BaseModel], _name: str, _field: Field):
            if not _name.startswith("xx_"):
                return orig_add_field(model_cls, _name, _field)
            setattr(model_cls, _name, _field)
            _field._toplevel = True
            # Use the stored definition for the specific field name so that
            # re-adding other xx_ fields during _setup_models__ keeps their
            # original definition instead of the current closure's field value.
            _field.definition = cls._xx_field_definitions.get(_name)
            _field.__set_name__(model_cls, _name)
            # add field as an attribute and in model_cls._fields__ (for reflection)
            model_cls._fields__[_name] = _field

        with patch("odoo.orm.model_classes.add_field", new=add_field):
            if field._args__.get("translate", False):
                translate = "standard"
                if field.type == "html":
                    translate = "html_translate"
                return cls.env["ir.model.fields"].create(
                    {
                        "model": model.model,
                        "model_id": model.id,
                        "name": name,
                        "field_description": field._args__["string"],
                        "ttype": field.type,
                        "translate": translate,
                        "store": True,
                    }
                )
            return cls.env["ir.model.fields"].create(
                {
                    "model": model.model,
                    "model_id": model.id,
                    "name": name,
                    "field_description": field._args__["string"],
                    "ttype": field.type,
                    "store": True,
                }
            )

    def _check_currency(self, root, company_ref, currency_ref):
        required_refs = {f"ref('{company_ref}')", f"ref('{currency_ref}')"}
        for function in root.findall(".//function"):
            if (
                function.attrib.get("model") == "res.company"
                and function.attrib.get("name") == "_dyn_export_fix_currency"
            ):
                found_refs = {value.attrib.get("eval", "") for value in function.findall("value")}
                self.assertTrue(required_refs.issubset(found_refs))
                return True
        return False

    def _check_translations(self, root, object_ref, field_name):
        odoo_object = self.env.ref(object_ref)
        # Iterate through all <function> tags in the XML
        for function in root.findall(".//function"):
            # Check if the function matches the target model and function name
            if (
                function.attrib.get("model") == odoo_object._name
                and function.attrib.get("name") == "_dyn_export_update_translations"
            ):
                # Check for <value eval="ref(...)"> inside this function
                for value in function.findall("value"):
                    eval_attr = value.attrib.get("eval", "")
                    if eval_attr == f"ref('{object_ref}')":
                        value = function.findall(".//value")[1].text
                        self.assertIn(f'"{field_name}": {{', value)
                        for lang in odoo_object._dyn_export_get_installed_languages():
                            self.assertIn(
                                odoo_object.with_context(lang=lang.code)[field_name], value
                            )
                        return True
        return False


class TestExportSettingsCommonController(TestExportSettingsCommon, common.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wizard._compute_settings()
