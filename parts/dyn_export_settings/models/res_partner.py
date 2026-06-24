import lxml.etree as etree

from odoo import models


class Partner(models.Model):
    _inherit = ["res.partner", "dyn.export.settings.mixin"]
    _name = "res.partner"

    @staticmethod
    def _dyn_export_get_export_order():
        return 3

    def _dyn_export_fields_to_ignore(self):
        return super()._dyn_export_fields_to_ignore() + [
            "barcode",
            # Fields from module calendar
            "calendar_last_notif_ack",
            # Fields from module mail
            "message_partner_ids",
            # Fields from module product
            "property_product_pricelist",
            "specific_property_product_pricelist",
            # TODO: Following fields should be moved to dyn_export_settings_website
            "website_id",
        ]

    def _dyn_export_binary_fields_to_export(self):
        return super()._dyn_export_binary_fields_to_export() + [
            "image_1920",
        ]

    def _dyn_export_binary_field(self, tag, key):
        if key == "image_1920":
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
                    f"/static/img/{filename}"
                    f"{self._get_file_extension(self, key)}",
                },
            )
        else:
            return super()._dyn_export_binary_field(tag, key)

    def _dyn_export_get_domain(self):
        return [("id", "in", self._dyn_export_get_companies().mapped("partner_id").ids)]

    def _dyn_export_setting_valid_for_export(self, _field):
        if _field.name == "street" and hasattr(self, "street_name"):
            return False
        if _field.name in ["peppol_endpoint", "vat", "account_sepa_lei"]:
            if not self[_field.name]:
                return False
        return super()._dyn_export_setting_valid_for_export(_field)

    def _dyn_export_add_xml_id_at_create(self, overwrite=False):
        if overwrite or self.env.context.get("create_from_model", "") == "res.company":
            return True
        return False
