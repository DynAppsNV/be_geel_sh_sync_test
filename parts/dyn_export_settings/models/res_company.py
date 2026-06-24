import logging

import lxml.etree as etree

from odoo import api, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = ["res.company", "dyn.export.settings.mixin"]
    _name = "res.company"

    @api.model_create_multi
    def create(self, vals_list):
        return super(ResCompany, self.with_context(create_from_model="res.company")).create(
            vals_list
        )

    def _dyn_export_fix_currency(self, currency_id, raise_exception=False):
        try:
            with self.env.cr.savepoint():
                self.currency_id = currency_id
        except Exception as e:
            _logger.error(f"_dyn_export_fix_currency: {e}")
            if raise_exception:
                raise e

    @staticmethod
    def _dyn_export_get_export_order():
        return 4

    def _dyn_export_fields_to_ignore(self):
        return (
            super()._dyn_export_fields_to_ignore()
            + super()._get_company_address_field_names()
            + [
                "alias_domain_id",
                "color",
                "user_ids",
                # Fields from module hr_timesheet
                "internal_project_id",
                # Fields from module timesheet_grid
                "timesheet_mail_employee_nextdate",
                "timesheet_mail_nextdate",
                # Fields from module project_timesheet_holidays
                "leave_timesheet_task_id",
            ]
        )

    def _dyn_export_binary_fields_to_export(self):
        return super()._dyn_export_binary_fields_to_export() + [
            "layout_background_image",
        ]

    def _dyn_export_setting_valid_for_export(self, _field):
        if _field.name in ["parent_id"]:
            if not self[_field.name]:
                return False
        return super()._dyn_export_setting_valid_for_export(_field)

    def _dyn_export_get_company_settings(self):
        company_settings = {}
        for company in self._dyn_export_get_companies():
            company_settings.setdefault(company.name, company._dyn_export_get_settings())
        return company_settings

    def _dyn_export_get_tech(self):
        if (
            self.env.context.get("module_data", self.env["xx.module.data"]).module_id
            == self._dyn_export_get_base_module()
        ):
            root = self._dyn_export_get_root_xml()
            company_settings = self._dyn_export_get_company_settings()
            self._dyn_export_add_main_company(root, company_settings)
            self._dyn_export_add_other_companies(root, company_settings)
            self._dyn_export_add_users_companies(root)
            return self._dyn_export_parse_xml(root)
        else:
            return super()._dyn_export_get_tech()

    def _dyn_export_get_func(self):
        company_settings_func = ""
        for company, values in (
            self.with_context(keep_original_xml_id=True)._dyn_export_get_company_settings().items()
        ):
            length = len(company) + 2
            company_settings_func += (
                ("-" * length + "\n") + f"# {company}\n" + ("-" * length + "\n")
            )
            company_settings_func += "\n".join(
                sorted(
                    self._dyn_export_translate_setting(
                        k,
                        v,
                        model="res.company",
                        use_func_descr=True,
                    )
                    for k, v in values.items()
                )
            )
            company_settings_func += "\n"
        return company_settings_func

    def _dyn_export_ignore_main_company_fields(self):
        return ["currency_id"]

    @staticmethod
    def _dyn_export_ignore_other_company_fields():
        return ["logo", "name", "partner_id"]

    def _dyn_export_pre_add_main_company(self, tag):
        return True

    def _dyn_export_pre_add_other_company_data(self, tag):
        partner_xml_id = self.partner_id._dyn_export_get_xml_id()
        etree.SubElement(
            tag,
            "field",
            attrib={
                "name": "name",
                "eval": f"obj(ref('{partner_xml_id}')).name",
                "model": "res.partner",
            },
        )
        etree.SubElement(
            tag,
            "field",
            attrib={
                "name": "partner_id",
                "ref": f"{partner_xml_id}",
            },
        )
        etree.SubElement(
            tag,
            "field",
            attrib={
                "name": "logo",
                "eval": f"obj(ref('{partner_xml_id}')).image_1920",
                "model": "res.partner",
            },
        )
        return True

    def _dyn_export_post_add_main_company(self, tag, settings_company):
        self._dyn_export_add_translations(tag, settings_company)
        self._dyn_export_add_fix_currency(tag)
        return True

    def _dyn_export_post_add_other_company(self, tag, settings_company):
        self._dyn_export_add_translations(tag, settings_company)
        return True

    def _dyn_export_add_main_company(self, tag, settings):
        main_company = self.env.ref("base.main_company")
        settings_main_company = settings.get(main_company.name)
        main_company._dyn_export_pre_add_main_company(tag)
        main_company_xml = etree.SubElement(
            tag,
            "record",
            attrib={"id": main_company._dyn_export_get_xml_id(), "model": "res.company"},
        )
        for k, v in settings_main_company.items():
            if main_company._fields[k].translate:
                continue
            if k in self._dyn_export_ignore_main_company_fields():
                continue
            main_company._dyn_export_get_field_xml(main_company_xml, main_company._name, k, v)
        main_company._dyn_export_post_add_main_company(tag, settings_main_company)
        return True

    def _dyn_export_add_other_companies(self, tag, settings):
        for company in self._dyn_export_get_companies(exclude_main_company=True):
            settings_company = settings.get(company.name)
            company_xml = etree.SubElement(
                tag,
                "record",
                attrib={
                    "id": company._dyn_export_get_xml_id(),
                    "model": "res.company",
                },
            )
            company._dyn_export_pre_add_other_company_data(company_xml)
            for k, v in settings_company.items():
                if k not in self._dyn_export_ignore_other_company_fields():
                    company._dyn_export_get_field_xml(company_xml, company._name, k, v)
            company._dyn_export_post_add_other_company(tag, settings_company)
        return True

    def _dyn_export_add_users_companies(self, tag):
        other_companies = self._dyn_export_get_companies(exclude_main_company=True)
        if other_companies:
            user_root_xml = etree.SubElement(
                tag, "record", attrib={"id": "base.user_root", "model": "res.users"}
            )
            self._dyn_export_get_field_xml(
                user_root_xml,
                "res.users",
                "company_ids",
                {
                    company.id: company._dyn_export_get_xml_id() for company in other_companies
                }.values(),
            )
            user_admin_xml = etree.SubElement(
                tag, "record", attrib={"id": "base.user_admin", "model": "res.users"}
            )
            self._dyn_export_get_field_xml(
                user_admin_xml,
                "res.users",
                "company_ids",
                {
                    company.id: company._dyn_export_get_xml_id() for company in other_companies
                }.values(),
            )
        return True

    def _dyn_export_add_fix_currency(self, tag):
        _tag = etree.SubElement(
            tag, "function", attrib={"model": "res.company", "name": "_dyn_export_fix_currency"}
        )
        etree.SubElement(_tag, "value", attrib={"eval": f"ref('{self._dyn_export_get_xml_id()}')"})
        etree.SubElement(
            _tag,
            "value",
            attrib={"eval": f"ref('{self.currency_id.get_external_id()[self.currency_id.id]}')"},
        )
