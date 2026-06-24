import logging

import lxml.etree as etree

from odoo import models
from odoo.tools import config

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    def update(self, values):
        if self.env.context.get("dyn_export_load_chart_template", False):
            values.pop("totals_below_sections", None)
            values.pop("account_tax_periodicity_reminder_day", None)
        return super().update(values)

    def _dyn_export_fix_account_price_include(self, account_price_include, raise_exception=False):
        try:
            with self.env.cr.savepoint():
                self.account_price_include = account_price_include
        except Exception as e:
            _logger.error(f"_dyn_export_fix_account_price_include: {e}")
            if raise_exception:
                raise e

    def _dyn_export_load_chart_template(self, template_code):
        if self.chart_template != template_code:
            if hasattr(self.env.registry, "_auto_install_template"):
                del self.env.registry._auto_install_template
            try:
                with self.env.cr.savepoint():
                    self.env["account.chart.template"].with_context(
                        dyn_export_load_chart_template=True
                    ).try_loading(
                        template_code=template_code, company=self, install_demo=config["with_demo"]
                    )
            except Exception as e:
                _logger.error(f"_dyn_export_load_chart_template: {e}")

    def _dyn_export_fields_to_ignore(self):
        return (
            super()._dyn_export_fields_to_ignore()
            + super()._get_company_address_field_names()
            + [
                # Fields from module account
                "account_price_include",  # _dyn_export_add_fix_account_price_include
                "batch_payment_sequence_id",
                "chart_template",  # _dyn_export_add_load_chart_template
                # Fields from module account_accountant
                "fiscalyear_lock_date",
                "hard_lock_date",
                "purchase_lock_date",
                "sale_lock_date",
                "tax_lock_date",
                # Fields from module account_peppol
                "account_peppol_proxy_state",
                # Fields from module account_reports
                "account_representative_id",
            ]
        )

    def _dyn_export_setting_valid_for_export(self, _field):
        if _field.name in ["account_peppol_phone_number"]:
            if not self[_field.name]:
                return False
        return super()._dyn_export_setting_valid_for_export(_field)

    def _dyn_export_pre_add_main_company(self, tag):
        result = super()._dyn_export_pre_add_main_company(tag)
        self._dyn_export_add_load_chart_template(tag)
        return result

    def _dyn_export_post_add_main_company(self, tag, settings_company):
        result = super()._dyn_export_post_add_main_company(tag, settings_company)
        self._dyn_export_add_fix_account_price_include(tag)
        return result

    def _dyn_export_post_add_other_company(self, tag, settings_company):
        result = super()._dyn_export_post_add_other_company(tag, settings_company)
        self._dyn_export_add_load_chart_template(tag)
        self._dyn_export_add_fix_account_price_include(tag)
        return result

    def _dyn_export_add_load_chart_template(self, tag):
        if self.chart_template:
            _tag = etree.SubElement(
                tag,
                "function",
                attrib={"model": "res.company", "name": "_dyn_export_load_chart_template"},
            )
            etree.SubElement(
                _tag, "value", attrib={"eval": f"ref('{self._dyn_export_get_xml_id()}')"}
            )
            etree.SubElement(_tag, "value").text = self.chart_template

    def _dyn_export_add_fix_account_price_include(self, tag):
        _tag = etree.SubElement(
            tag,
            "function",
            attrib={"model": "res.company", "name": "_dyn_export_fix_account_price_include"},
        )
        etree.SubElement(_tag, "value", attrib={"eval": f"ref('{self._dyn_export_get_xml_id()}')"})
        etree.SubElement(_tag, "value").text = self.account_price_include
