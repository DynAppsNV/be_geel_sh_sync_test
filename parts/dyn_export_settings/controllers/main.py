import os
import tempfile
import zipfile

from odoo import http
from odoo.http import content_disposition, request


class ZipDownloadController(http.Controller):
    @http.route("/web/dynapps/settings/download/<int:export_settings_id>", type="http", auth="user")
    def download(self, export_settings_id, **kwargs):
        export_settings = (
            request.env["xx.dynapps.export.settings"].sudo().browse(export_settings_id)
        )
        # Create a temporary zip file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
            zip_filename = temp_zip.name  # Get the name of the temporary file
            # Create a new zip file
            with zipfile.ZipFile(zip_filename, "w") as _zipfile:
                custom_path = "parts/custom/"
                base_module_path = os.path.join(
                    custom_path,
                    request.env["dyn.export.settings.mixin"]
                    .sudo()
                    ._dyn_export_get_base_module()
                    .name,
                )
                for module in export_settings.module_data_ids.mapped("module_id"):
                    module_name = module.name
                    data_files = []
                    for module_data in export_settings.module_data_ids.filtered(
                        lambda x, m=module: x.module_id == m
                    ).sorted("export_order"):
                        if module_data.settings_tech:
                            _zipfile.writestr(
                                os.path.join(
                                    custom_path, module_name, "data", module_data.data_filename
                                ),
                                module_data.settings_tech,
                            )
                            data_files.append(f"data/{module_data.data_filename}")
                    manifest_data = export_settings.get_updated_manifest_data(module, data_files)
                    _zipfile.writestr(
                        os.path.join(custom_path, module_name, "__manifest__.py"),
                        repr(manifest_data),
                    )
                if export_settings.disabled_modules_tech:
                    _zipfile.writestr("dyn-build.yaml", export_settings.get_updated_build_data())
                image_path = os.path.join(base_module_path, "static/img/")
                for model in (
                    request.env["ir.model"]
                    .search([])
                    .filtered(
                        lambda r: isinstance(
                            request.env.get(r.model),
                            request.env.registry["dyn.export.settings.mixin"],
                        )
                    )
                ):
                    for binary_field_to_export in request.env[
                        model.model
                    ]._dyn_export_binary_fields_to_export():
                        if model.model == "res.partner" and binary_field_to_export == "image_1920":
                            for partner_logo in export_settings.partner_logo_ids:
                                attachment = (
                                    request.env["dyn.export.settings.mixin"]
                                    .sudo()
                                    ._get_attachment(partner_logo.partner_id, "image_1920")
                                )
                                _zipfile.writestr(
                                    os.path.join(image_path, partner_logo.filename), attachment.raw
                                )
                        elif model.model == "res.company":
                            for record in request.env[model.model].search([]):
                                attachment = (
                                    request.env["dyn.export.settings.mixin"]
                                    .sudo()
                                    ._get_attachment(record, binary_field_to_export)
                                )
                                if attachment:
                                    company_xml_id = record._dyn_export_get_xml_id().split(".")[
                                        -1:
                                    ][0]
                                    extension = request.env[
                                        "dyn.export.settings.mixin"
                                    ]._get_file_extension(record, binary_field_to_export)
                                    filename = (
                                        f"{company_xml_id}_{binary_field_to_export}{extension}"
                                    )
                                    _zipfile.writestr(
                                        os.path.join(
                                            base_module_path,
                                            "static/img/",
                                            filename,
                                        ),
                                        attachment.raw,
                                    )
            # Read the zip file to return it in the response
            with open(zip_filename, "rb") as _zipfile:
                zip_data = _zipfile.read()
            # Return the zip file as a downloadable response
            response = request.make_response(
                zip_data,
                headers=[
                    ("Content-Type", "application/zip"),
                    ("Content-Disposition", content_disposition("settings.zip")),
                ],
            )
        return response
