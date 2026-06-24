import datetime
import difflib
import json
import logging
import mimetypes
import os
import re
import xml.dom.minidom

import lxml.etree as etree
from psycopg2._json import Json

from odoo import api, models
from odoo.tools import file_open, file_path
from odoo.tools.convert import safe_eval

_logger = logging.getLogger(__name__)


class DynExportSettingsMixin(models.AbstractModel):
    _name = "dyn.export.settings.mixin"
    _description = "Dyn Export Settings Mixin"

    # automatically create xml_id for new records
    def _load_records(self, data_list, update=False):
        return super(
            DynExportSettingsMixin, self.with_context(install_model=self._name)
        )._load_records(data_list, update=update)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._dyn_export_add_xml_id()
        return records

    def __dyn_export_get_base_module_name(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("dyn_export_settings.base_module_name", "xx_base")
        )

    def _dyn_export_get_base_module(self):
        return self.env["ir.module.module"].search(
            [("name", "=", self.__dyn_export_get_base_module_name())]
        ) or self.env.ref("base.module_dyn_export_settings")

    def _dyn_export_get_installed_languages(self):
        return self.env["res.lang"].browse(
            [data.id for data in self.env["res.lang"]._get_active_by("code").values()]
        )

    def _dyn_export_get_companies(self, exclude_main_company=False):
        domain = [("active", "=", True), ("user_ids", "in", self.env.uid)]
        if exclude_main_company:
            domain.append(("id", "!=", self.env.ref("base.main_company").id))
        return self.env["res.company"].sudo().search(domain)

    # _dyn_export_fields_to_ignore can be used to exclude fields from the export
    def _dyn_export_fields_to_ignore(self):
        return models.MAGIC_COLUMNS

    def _dyn_export_ignore_field(self, field_name):
        if (
            self._dyn_export_is_secret_field(field_name)
            or field_name in self._dyn_export_fields_to_ignore()
        ):
            return True
        _field = self._fields[field_name]
        if _field.compute:
            # Non-stored fields are not exported
            if not (_field.store or _field.inverse):
                return True
            # Readonly stored fields are not exported
            if _field.store and _field.readonly:
                return True
        if _field.related:
            return True
        if _field.relational:
            if _field.type == "one2many":
                return True
        if _field.type == "properties":
            return True
        return False

    # _dyn_export_binary_fields_to_export can be used to specify binary fields that
    # should be exported
    def _dyn_export_binary_fields_to_export(self):
        return []

    @staticmethod
    def _dyn_export_allowed_secret_fields():
        return ["auth_signup_reset_password"]

    def _dyn_export_is_secret_field(self, field):
        secret_keywords = ["password", "passwd", "pwd", "secret", "token", "key"]
        allowed_secret_fields = self._dyn_export_allowed_secret_fields()

        # Check if the field is secret
        is_secret = any(
            field.startswith(keyword) or f"_{keyword}" in field for keyword in secret_keywords
        )

        # If it's secret, check if it's allowed
        if is_secret and field not in allowed_secret_fields:
            return True  # The field is secret and not allowed
        return False  # The field is either not secret or is allowed

    def _dyn_export_get_installed_modules(self):
        base_module = self._dyn_export_get_base_module()
        base_module_downstream_dependencies = base_module.downstream_dependencies().mapped("name")
        return [
            module.name
            for module in self.env["ir.module.module"].search(
                [
                    ("state", "=", "installed"),
                    ("name", "not in", ("studio_customization", base_module.name)),
                ]
            )
            if module.name not in base_module_downstream_dependencies
        ]

    def _dyn_export_get_object_value(self, object_ref, field_name):
        try:
            odoo_object = self.env.ref(object_ref).sudo()
            return odoo_object[field_name]
        except ValueError as e:
            return e.args[0]

    def _dyn_export_translate_setting(self, key, value, model, use_func_descr=False):  # noqa: C901
        _field = self.env[model]._fields[key]
        _value = value
        dict_values_type = type({}.values())
        if isinstance(value, str | datetime.date | datetime.datetime):
            if not use_func_descr:
                return f"'{key}': '{_value}'"
        if isinstance(value, dict_values_type):
            if _field.type == "many2one":
                if use_func_descr:
                    _value = self._dyn_export_get_object_value(list(_value)[0], "display_name")
                else:
                    _value = f"obj().env.ref('{list(_value)[0]}').id"
            else:
                if use_func_descr:
                    _values = []
                    for v in list(_value):
                        if v:
                            _values.append(self._dyn_export_get_object_value(v, "display_name"))
                    _value = ", ".join(_values)
                else:
                    _value = ", ".join(f"obj().env.ref('{v}').id" for v in list(_value) if v)
                    _value = f"[{_value}]"
        if use_func_descr:
            if _field.type == "selection":
                selection = False
                if isinstance(_field.selection, list):
                    selection = dict(_field.selection)
                elif callable(_field.selection):
                    selection = dict(_field.selection(self))
                elif hasattr(self, _field.selection):
                    selection = dict(getattr(self, _field.selection)())
                if selection:
                    return f"{_field.string} ({key}): {selection.get(_value)} ({_value})"
            elif _field._args__ and _field._args__.get("translate"):
                values = []
                for language in self._dyn_export_get_installed_languages():
                    _value = getattr(self.with_context(lang=language.code), key)
                    values.append(f"\n  {language.code}: {_value}")
                return f"{_field.string} ({key}): {''.join(values)}"
            return f"{_field.string} ({key}): {_value}"
        else:
            return f"'{key}': {_value}"

    def _dyn_export_record_valid_for_export(self):
        return True

    def _dyn_export_valid_for_module(self, _field):
        module_model_data = self.env.context.get(
            "module_data", self.env["xx.module.data"]
        ).filtered(lambda r: r.model_id.model == self._name)
        if module_model_data:
            if module_model_data.module_id == self._dyn_export_get_base_module():
                # Take into account all fields in all custom modules
                module_custom_fields = module_model_data.settings_id.custom_field_ids.filtered(
                    lambda r: r.module_id != module_model_data.module_id
                    and r.model_id == module_model_data.model_id
                )
                if _field.name in module_custom_fields.field_ids.mapped("name"):
                    return False
            else:
                # Take into account all fields of the specific custom modules
                module_custom_fields = module_model_data.settings_id.custom_field_ids.filtered(
                    lambda r: r.module_id == module_model_data.module_id
                    and r.model_id == module_model_data.model_id
                )
                if (
                    module_custom_fields
                    and _field.name not in module_custom_fields.field_ids.mapped("name")
                ):
                    return False
        return True

    def _dyn_export_setting_valid_for_export(self, _field):
        if _field.name.startswith("x_"):
            return False
        elif not self._dyn_export_valid_for_module(_field):
            return False
        elif (
            _field.type in ["date", "datetime", "selection", "html", "text"]
            and not self[_field.name]
        ):
            return False
        elif hasattr(_field, "translate") and _field.translate:
            return False
        elif _field.name in ["xx_external_id", "xx_external_source"]:
            if not self[_field.name]:
                return False
        return True

    def _dyn_export_get_settings(self):
        self.ensure_one()
        record = self
        record_setting = {}
        company = getattr(record, "company_id", None)
        _record = record.with_company(company) if company else record
        for field in list(_record.fields_get()):
            if self._dyn_export_ignore_field(field):
                continue
            _field = _record._fields[field]
            if _field.relational:
                if hasattr(_record[field], "_dyn_export_get_xml_id"):
                    relational_values = {
                        x.id: x._dyn_export_get_xml_id() for x in _record[field]
                    }.values()
                else:
                    relational_values = _record[field].get_external_id().values()
                if any(relational_values):
                    record_setting[field] = relational_values
                else:
                    if _field.type == "many2one":
                        record_setting[field] = False
                    else:
                        record_setting[field] = []
            elif _field.type == "char":
                record_setting[field] = _record[field] or ""
            elif _field.type == "serialized":
                record_setting[field] = json.dumps(_record[field] or {})
            else:
                record_setting[field] = _record[field]
        return dict(sorted(record_setting.items()))

    # Get the prefix for generated xml_id's
    def _dyn_export_get_xml_id_prefix(self):
        return self._name.replace(".", "_")

    # Get the name of the field that has to be used for the xml_id
    def _dyn_export_get_xml_id_name(self, field_name="name"):
        name = re.sub(r"\W+", "_", self[field_name].lower()).strip("_")
        # Add company external id to the name
        if hasattr(self, "company_id") and self.company_id:
            company_xml_id = self.company_id._dyn_export_get_xml_id().split(".")[-1:][0]
            name = f"{company_xml_id}_{name}"
        return name

    # Get or generate the xml_id
    def _dyn_export_get_xml_id(self):
        module = (
            self.env.context.get("module_data", self.env["xx.module.data"]).module_id
            or self._dyn_export_get_base_module()
        )
        self.ensure_one()
        xml_id = (
            self.get_external_id()[self.id]
            or f"{module.name}.{self._dyn_export_get_xml_id_prefix()}_"
            + self._dyn_export_get_xml_id_name()
        )
        if self.env.context.get("keep_original_xml_id", False):
            return xml_id
        return xml_id.removeprefix(f"{module.name}.")

    def _dyn_export_sort_records(self):
        return self

    def _dyn_export_get_domain(self):
        return []

    def _dyn_export_get_records(self, order="id asc", limit=None):
        active_test = False
        if self._name == "res.company":
            active_test = True
        records = self.with_context(
            allowed_company_ids=self._dyn_export_get_companies().ids, active_test=active_test
        ).search(self._dyn_export_get_domain(), order=order, limit=limit)
        return records._dyn_export_sort_records()

    def _dyn_export_build_tech_xml(self, tag):
        for record in self._dyn_export_get_records():
            if not record._dyn_export_record_valid_for_export():
                continue
            attributes = {
                "id": record._dyn_export_get_xml_id(),
                "model": record._name,
            }
            temp_xml = etree.Element("temp", attrib=attributes)
            settings = record._dyn_export_get_settings()
            for k, v in settings.items():
                record._dyn_export_get_field_xml(temp_xml, record._name, k, v)
            if len(temp_xml):
                record_xml = etree.SubElement(tag, "record", attrib=attributes)
                for child in temp_xml:
                    record_xml.append(child)
            record._dyn_export_add_translations(tag, settings)

    def _dyn_export_get_tech(self):
        temp_xml = etree.Element("temp")
        self._dyn_export_build_tech_xml(temp_xml)
        if len(temp_xml):
            root = self._dyn_export_get_root_xml()
            for child in temp_xml:
                root.append(child)
            return self._dyn_export_parse_xml(root)
        return ""

    def _dyn_export_relational_field(self, tag, key, _field, _value):
        downstream_modules = (
            self.env.context.get("module_data", self.env["xx.module.data"])
            .module_id.downstream_dependencies()
            .mapped("name")
        )
        # Filter based on following conditions:
        # 1. Not containing any '{excl}.' -> Excluding values from downstream modules
        # 2. Not containing '.x_' -> Excluding x_ Studio Fields
        # 3. Not starting with '__export__.' -> Excluding not defined values
        filtered_values = [
            val
            for val in _value
            if not any(f"{excl}." in val for excl in downstream_modules)
            and ".x_" not in val
            and not val.startswith("__export__.")
        ]
        if filtered_values:
            if _field.type == "many2one":
                etree.SubElement(tag, "field", attrib={"name": key, "ref": filtered_values[0]})
            else:
                value = ", ".join(f"Command.link(ref('{v}'))" for v in filtered_values)
                value = f"[{value}]"
                etree.SubElement(tag, "field", attrib={"name": key, "eval": value})

    def _get_attachment(self, record, key):
        return (
            self.env["ir.attachment"]
            .with_context(skip_res_field_check=True)
            .sudo()
            .search(
                [
                    ("res_model", "=", record._name),
                    ("res_id", "=", record.id),
                    ("res_field", "=", key),
                ]
            )
        )

    def _get_file_extension(self, record, key):
        attachment = self._get_attachment(record, key)
        if not attachment:
            return ".png"
        return mimetypes.guess_extension(attachment.mimetype)

    def _dyn_export_binary_field(self, tag, key):
        _field = self.env[self._name]._fields[key]
        if _field.attachment and self[key]:
            if "." in tag.attrib["id"]:
                filename = tag.attrib["id"].split(".")[-1:][0]
            else:
                filename = tag.attrib["id"]
            etree.SubElement(
                tag,
                "field",
                attrib={
                    "name": key,
                    "type": "base64",
                    "file": f""
                    f"{self._dyn_export_get_base_module().name}"
                    f"/static/img/{filename}_{key}"
                    f"{self._get_file_extension(self, key)}",
                },
            )

    def _dyn_export_get_field_xml(self, tag, model, key, value):
        _field = self.env[model]._fields[key]
        _value = value
        dict_values_type = type({}.values())
        if not self._dyn_export_setting_valid_for_export(_field):
            return
        elif isinstance(value, dict_values_type):
            self._dyn_export_relational_field(tag, key, _field, _value)
        elif _field.type == "binary":
            if _field.name in self._dyn_export_binary_fields_to_export():
                self._dyn_export_binary_field(tag, key)
        else:
            if (_field.relational and not value) or _field.type == "properties_definition":
                etree.SubElement(tag, "field", attrib={"name": key, "eval": str(value)})
            else:
                etree.SubElement(tag, "field", attrib={"name": key}).text = str(value)

    @staticmethod
    def _dyn_export_get_root_xml():
        return etree.Element("odoo", attrib={"noupdate": "1"})

    @staticmethod
    def _dyn_export_parse_xml(root, placeholder=None):
        rough_string = etree.tostring(root, encoding="utf-8", method="xml")
        pretty_xml_as_string = xml.dom.minidom.parseString(rough_string).toprettyxml(indent="    ")
        if placeholder:
            pretty_xml_as_string = pretty_xml_as_string.replace("<placeholder/>", placeholder)
        pretty_xml_as_string = "\n".join(pretty_xml_as_string.split("\n")[1:])
        # Manually add space before '/>' for self-closing tag
        pretty_xml_as_string = pretty_xml_as_string.replace('"/>', '" />')
        xml_declaration = '<?xml version="1.0" encoding="UTF-8" ?>\n'
        return xml_declaration + pretty_xml_as_string

    def _dyn_export_add_xml_id(self, overwrite=False):
        if overwrite:
            for record in self.filtered(
                lambda r: r._dyn_export_add_xml_id_at_create(overwrite)
                and r._dyn_export_get_xml_id().startswith("__export__")
            ):
                self.env["ir.model.data"].search(
                    [
                        ("module", "=", "__export__"),
                        ("model", "=", record._name),
                        ("name", "=", record._dyn_export_get_xml_id().split(".")[-1:][0]),
                    ]
                ).unlink()
        for record in self.filtered(lambda r: not r.get_external_id()[r.id]):
            if record._dyn_export_add_xml_id_at_create(overwrite):
                self.env["ir.model.data"]._update_xmlids(
                    [
                        {
                            "xml_id": record.with_context(
                                keep_original_xml_id=True
                            )._dyn_export_get_xml_id(),
                            "noupdate": True,
                            "record": record,
                        },
                    ],
                )

    def _dyn_export_add_xml_id_at_create(self, overwrite=False):
        self.ensure_one()
        if self.env.context.get("skip_xml_id_at_create", False) or (
            self.env.context.get("install_mode", False)
            and self.env.context.get("install_model") == self._name
        ):
            return False
        return True

    def _dyn_export_get_func(self):
        result = ""
        for record in self._dyn_export_get_records():
            name = record.name
            setting = record._dyn_export_get_settings()
            settings_str = "\n".join([f"-{k}: {v}" for k, v in setting.items()])
            result += f"{name}\n{settings_str}\n\n"
        return result

    @staticmethod
    def _dyn_export_normalize_xml(content):
        """Replace newlines and spaces outside CDATA and **{} sections"""

        # Remove extra spaces within opening tags (like <value >)
        content = re.sub(r"<(\w+)\s+>", r"<\1>", content)
        # Remove spaces before closing '>'
        content = re.sub(r"\s+>", ">", content)
        # Remove extra spaces between the `>` and `<![CDATA[`
        content = re.sub(r">\s+<!\[CDATA", "><![CDATA", content)
        # Remove all unnecessary spaces outside CDATA and **{} sections
        content = re.sub(r"\s+(?![^\[]*\]\]>)(?![^{]*\})", " ", content.strip())
        # Join opening tag attributes onto a single line
        content = re.sub(r"<(\w+)([^>]*)\s*\n\s*([^>]*)>", r"<\1\2\3>", content)

        # Remove spaces between tags
        content = re.sub(r">\s+<", ">\n<", content)

        return content

    def _dyn_export_normalize_whitespace(self, content):
        # Replace multiple spaces with a single space and strip leading/trailing spaces
        return " ".join(self._dyn_export_normalize_xml(content).split())

    def _dyn_export_get_diff(self, current_content_path, new_content):
        try:
            with open(file_path(current_content_path)) as file:
                old_content = file.read()
        except FileNotFoundError:
            old_content = ""
        if bool(
            "\n".join(
                difflib.unified_diff(
                    self._dyn_export_normalize_whitespace(old_content).splitlines(),
                    self._dyn_export_normalize_whitespace(new_content).splitlines(),
                    lineterm="",
                )
            ).strip()
        ):
            return "\n".join(
                difflib.unified_diff(
                    self._dyn_export_normalize_xml(old_content).splitlines(),
                    self._dyn_export_normalize_xml(new_content).splitlines(),
                    lineterm="",
                )
            )
        return ""

    def _dyn_export_update_translations(self, translations):
        translations2update = {}
        for field_name, translation in json.loads(translations).items():
            translations2update[field_name] = Json(translation)
        self._write(translations2update)

    def _dyn_export_add_translations(self, tag, settings):
        translations = {}
        for language in self._dyn_export_get_installed_languages():
            translated_fields = {
                _field: self.with_context(lang=language.code)[_field]
                for _field in [
                    field_name
                    for field_name, field_def in self._fields.items()
                    if field_def.translate
                    and field_name in settings.keys()
                    and self[field_name]
                    and self._dyn_export_valid_for_module(field_def)
                ]
            }

            for _field, translated_value in translated_fields.items():
                if _field not in translations:
                    translations[_field] = {}
                translations[_field][language.code] = translated_value
        if translations:
            lang_xml = etree.SubElement(
                tag,
                "function",
                attrib={"model": self._name, "name": "_dyn_export_update_translations"},
            )
            etree.SubElement(
                lang_xml,
                "value",
                attrib={"eval": f"ref('{self._dyn_export_get_xml_id()}')"},
            )
            etree.SubElement(lang_xml, "value").text = etree.CDATA(
                json.dumps(translations, indent=4)
            )

    @staticmethod
    def _dyn_export_get_module_data_file_path(module, filename):
        return os.path.join(module.name, "data", filename)

    def _dyn_export_get_data_filename(self):
        return f"{self._name.replace('.', '_')}_data.xml"

    @staticmethod
    def _dyn_export_get_export_order():
        return 1000

    @staticmethod
    def _dyn_export_get_original_manifest_data(module):
        try:
            with file_open(os.path.join(module.name, "__manifest__.py"), "r") as file:
                manifest_data = safe_eval(file.read())
            return manifest_data
        except FileNotFoundError:
            return {}

    @staticmethod
    def _dyn_export_is_defined_in_module(_field, _model, _module):
        in_modules = [m.strip() for m in _field.modules.split(",")]
        if len(in_modules) == 1 and _field.modules == _module.name:
            return True
        if set(in_modules).issubset(
            _module.downstream_dependencies().mapped("name") + [_module.name]
        ):
            return True
        return False

    @staticmethod
    def _dyn_export_add_noupdate_xml(tag, records):
        function_noupdate = etree.SubElement(
            tag, "function", attrib={"model": "ir.model.data", "name": "write"}
        )
        value = ", ".join(f"ref('{v}')" for v in records.get_external_id().values())
        value = f"[{value}]"
        etree.SubElement(
            function_noupdate,
            "value",
            attrib={
                "model": "ir.model.data",
                "eval": f"obj().env['ir.model.data']."
                f"search([('model', '=', '{records._name}'), ('res_id', 'in', {value})]).ids",
            },
        )
        etree.SubElement(
            function_noupdate,
            "value",
            attrib={
                "eval": "{'noupdate': True}",
            },
        )
