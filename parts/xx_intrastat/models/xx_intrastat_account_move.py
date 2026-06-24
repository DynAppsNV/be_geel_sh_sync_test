from collections import defaultdict

from lxml import etree

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.account_intrastat.models.account_intrastat_code import SUPPLEMENTARY_UNITS

_merchandise_export_code = {
    "BE": "29",
    "FR": "21",
    "NL": "7",
}

_merchandise_import_code = {
    "BE": "19",
    "FR": "11",
    "NL": "6",
}


class IntrastatAccountMove(models.Model):
    _name = "xx.intrastat.account.move"
    _description = "Intrastat Account Move"

    move_id = fields.Many2one(string="Invoice", comodel_name="account.move", required=True)
    move_state = fields.Selection(related="move_id.state", string="Move State", store=True)

    invoice_date = fields.Date(string="Invoice Date", related="move_id.date", store=True)

    intrastat_code_id = fields.Many2one(
        string="Transaction",
        comodel_name="account.intrastat.code",
        domain=lambda self: [
            ("type", "=", "transaction"),
            "&",
            "|",
            ("expiry_date", ">", fields.Date.context_today(self)),
            ("expiry_date", "=", False),
            "|",
            ("start_date", "<=", fields.Date.context_today(self)),
            ("start_date", "=", False),
        ],
        required=True,
    )
    intrastat_commodity_code = fields.Many2one(
        string="Commodity",
        comodel_name="account.intrastat.code",
        domain=lambda self: [
            ("type", "=", "commodity"),
            "&",
            "|",
            ("expiry_date", ">", fields.Date.context_today(self)),
            ("expiry_date", "=", False),
            "|",
            ("start_date", "<=", fields.Date.context_today(self)),
            ("start_date", "=", False),
        ],
        required=True,
    )
    intrastat_country_code = fields.Many2one(
        "res.country",
        string="Country of Origin",
        help="Restrict the applicability of code to a country.",
        domain=[("country_group_ids.code", "=", "INTRASTAT")],
        required=True,
    )
    intrastat_supplementary_units_amount = fields.Float(string="Supplementary Units")
    intrastat_supplementary_units_code = fields.Selection(
        string="Supplementary Units Code", selection=SUPPLEMENTARY_UNITS
    )
    intrastat_weight = fields.Float(string="Weight (kg)")
    intrastat_value = fields.Float(string="Value")
    intrastat_statistical_value = fields.Float(string="Statistical Value")

    @api.onchange("move_id")
    def _onchange_move_id(self):
        for record in self:
            record._compute_defaults_from_move()

    def _compute_defaults_from_move(self):
        """Compute all default values for an Intrastat line based on move_id."""
        self.ensure_one()
        if not self.move_id:
            return

        # Default transaction code
        default_transaction = self.env["account.intrastat.code"].search(
            [("xx_default_transaction", "=", True)], limit=1
        )
        self.intrastat_code_id = default_transaction.id if default_transaction else False

        # Default commodity code from partner
        self.intrastat_commodity_code = (
            self.move_id.partner_id.xx_commodity_code_id.id
            if self.move_id.partner_id and self.move_id.partner_id.xx_commodity_code_id
            else False
        )

        # Default country from invoice
        self.intrastat_country_code = (
            self.move_id.intrastat_country_id.id if self.move_id.intrastat_country_id else False
        )

        # Compute remaining Intrastat value
        existing_lines_total = sum(self.move_id.xx_intrastat_line_ids.mapped("intrastat_value"))
        remaining_value = (
            sum(self.move_id.invoice_line_ids.mapped("price_total")) - existing_lines_total
        )
        if remaining_value > 0:
            self.intrastat_value = remaining_value
            self.intrastat_statistical_value = remaining_value
        else:
            self.intrastat_value = 0.0
            self.intrastat_statistical_value = 0.0

        if not self.intrastat_weight:
            self.intrastat_weight = 0.0
        if not self.intrastat_supplementary_units_amount:
            self.intrastat_supplementary_units_amount = 0

    @api.onchange("intrastat_commodity_code")
    def _onchange_intrastat_commodity_code(self):
        for record in self:
            record._compute_supplementary_units_code()

    def _compute_supplementary_units_code(self):
        self.ensure_one()
        self.intrastat_supplementary_units_code = (
            self.intrastat_commodity_code.supplementary_unit
            if self.intrastat_commodity_code
            else 0.0
        )

    @api.constrains("intrastat_supplementary_units_code", "intrastat_supplementary_units_amount")
    def _check_supplementary_units(self):
        for record in self:
            if (
                record.intrastat_supplementary_units_code
                and not record.intrastat_supplementary_units_amount
            ):
                raise ValidationError(
                    self.env._(
                        "Supplementary units amount is required"
                        " when a supplementary units code is set."
                    )
                )

    @api.onchange("intrastat_value")
    def _onchange_intrastat_value(self):
        for record in self:
            record._compute_statistical_value()

    def _compute_statistical_value(self):
        self.ensure_one()
        self.intrastat_statistical_value = self.intrastat_value

    def get_export_xml(self, declaration_type="extended"):
        """Generate intrastat XML.

        declaration_type: 'standard' → EX19S/EXF19S (8 core fields)
                          'extended' → EX19E/EXF19E (+ EXTPC, EXDELTRM)
        """
        records = self.filtered(lambda r: r.exists() and r.move_id.state == "posted")

        is_extended = declaration_type == "extended"
        report_code = "EX19E" if is_extended else "EX19S"
        form_code = "EXF19E" if is_extended else "EXF19S"

        nsmap = {None: "http://www.onegate.eu/2010-01-01"}
        root = etree.Element("DeclarationReport", nsmap=nsmap)
        administration = etree.SubElement(root, "Administration")

        if records:
            first_record = records[0]
            company = first_record.move_id.company_id
            vat_number = (
                company.vat[2:] if company.vat else company.company_registry or "N/A"
            )  # remove first 2 letters (country code)
            from_el = etree.SubElement(administration, "From", declarerType="KBO")
            from_el.text = vat_number

            to_el = etree.SubElement(administration, "To")
            to_el.text = "NBB"

            domain_el = etree.SubElement(administration, "Domain")
            domain_el.text = "SXX"

            report = etree.SubElement(
                root,
                "Report",
                action="append",
                date=first_record.move_id.date.strftime("%Y-%m"),
                code=report_code,
            )

            data = etree.SubElement(report, "Data", close="true", form=form_code)

            # Step 1: group records by key fields
            grouped_lines = defaultdict(list)
            for rec in records:
                move = rec.move_id
                company = move.company_id

                system_code = (
                    _merchandise_import_code.get(company.country_id.code, "29")
                    if move.move_type in ("in_invoice", "out_refund")
                    else _merchandise_export_code.get(company.country_id.code, "19")
                )
                transport = (
                    (
                        move.intrastat_transport_mode_id.code
                        or company.intrastat_transport_mode_id.code
                        or ""
                    )
                    if is_extended
                    else ""
                )
                incoterm = (
                    (move.invoice_incoterm_id.code or company.incoterm_id.code or "")
                    if is_extended
                    else ""
                )

                key = (
                    system_code,
                    move.intrastat_country_id.code if move.intrastat_country_id else "",
                    rec.intrastat_code_id.code if rec.intrastat_code_id else "",
                    company.intrastat_region_id.code if company.intrastat_region_id else "",
                    rec.intrastat_commodity_code.code if rec.intrastat_commodity_code else "",
                    rec.intrastat_supplementary_units_amount or 0,
                    transport,
                    incoterm,
                )
                grouped_lines[key].append(rec)

            # Step 2: create XML items
            for key, lines in grouped_lines.items():
                (
                    system_code,
                    country_code,
                    intrastat_code,
                    region_code,
                    commodity_code,
                    units,
                    transport,
                    incoterm,
                ) = key

                total_weight = sum(line.intrastat_weight or 0 for line in lines)
                total_value = sum(line.intrastat_value or 0 for line in lines)

                item = etree.SubElement(data, "Item")
                etree.SubElement(item, "Dim", prop="EXTRF").text = str(system_code)
                etree.SubElement(item, "Dim", prop="EXCNT").text = str(country_code)
                etree.SubElement(item, "Dim", prop="EXTTA").text = str(intrastat_code)
                etree.SubElement(item, "Dim", prop="EXREG").text = str(region_code)
                etree.SubElement(item, "Dim", prop="EXTGO").text = str(commodity_code)
                etree.SubElement(item, "Dim", prop="EXWEIGHT").text = str(total_weight)
                etree.SubElement(item, "Dim", prop="EXTXVAL").text = str(total_value)
                etree.SubElement(item, "Dim", prop="EXUNITS").text = str(units)
                if is_extended:
                    etree.SubElement(item, "Dim", prop="EXTPC").text = str(transport)
                    etree.SubElement(item, "Dim", prop="EXDELTRM").text = str(incoterm)

        return etree.tostring(root, pretty_print=True, encoding="utf-8", xml_declaration=True)
