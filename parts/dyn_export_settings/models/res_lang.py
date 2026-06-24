import logging

import lxml.etree as etree

from odoo import models

_logger = logging.getLogger(__name__)


class ResLang(models.Model):
    _inherit = ["res.lang", "dyn.export.settings.mixin"]
    _name = "res.lang"

    @staticmethod
    def _dyn_export_get_export_order():
        return 1

    def _dyn_export_get_records(self, order="id asc", limit=None):
        return self._dyn_export_get_installed_languages()

    def _dyn_export_get_tech(self):
        if (
            self.env.context.get("module_data", self.env["xx.module.data"]).module_id
            == self._dyn_export_get_base_module()
        ):
            root = self._dyn_export_get_root_xml()
            self._dyn_export_get_language_install(root)
            self._dyn_export_build_tech_xml(root)
            self._dyn_export_add_noupdate_xml(root, self._dyn_export_get_installed_languages())
            return self._dyn_export_parse_xml(root)
        else:
            return super()._dyn_export_get_tech()

    def _dyn_export_get_language_install(self, tag):
        language_xml = etree.SubElement(
            tag, "record", attrib={"id": "base_language_install", "model": "base.language.install"}
        )
        self.env["dyn.export.settings.mixin"]._dyn_export_get_field_xml(
            language_xml,
            "base.language.install",
            "lang_ids",
            self._dyn_export_get_installed_languages().get_external_id().values(),
        )
        function_install = etree.SubElement(
            tag, "function", attrib={"model": "base.language.install", "name": "lang_install"}
        )
        etree.SubElement(
            function_install,
            "value",
            attrib={
                "eval": f"ref('{self._dyn_export_get_base_module().name}.base_language_install')"
            },
        )

    def _dyn_export_get_func(self):
        self = self.with_context(lang="en_US")
        return "\n".join(
            sorted(
                f"{language.code} - {language.name}"
                for language in self._dyn_export_get_installed_languages()
            )
        )
