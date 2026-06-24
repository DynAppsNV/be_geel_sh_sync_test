from datetime import date
from io import BytesIO

from lxml import etree

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestIntrastat(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AccountMove = cls.env["account.move"]
        cls.AccountMoveLine = cls.env["account.move.line"]
        cls.IntrastatMove = cls.env["xx.intrastat.account.move"]

        company = cls.env.company
        company.write(
            {
                "vat": "BE0437278077",
                "company_registry": "0437.278.077",
            }
        )

        code_vals = [
            {"type": type, "name": f"{type}"}
            for type in ("commodity", "transaction", "region", "transport")
        ]
        cls.intrastat_codes = {}
        create_vals_list = []
        for i, vals in enumerate(code_vals, 100):
            v = vals.copy()
            v["code"] = str(i)
            if v["type"] == "commodity":
                v["supplementary_unit"] = "p/st"
            create_vals_list.append(v)
        cls.intrastat_codes = {
            x.name: x for x in cls.env["account.intrastat.code"].sudo().create(create_vals_list)
        }

        cls.intrastat_codes["transaction"].write({"xx_default_transaction": True})

        partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
            }
        )
        partner.write({"xx_commodity_code_id": cls.intrastat_codes["commodity"].id})

        cls.invoice = cls.AccountMove.create(
            {
                "move_type": "out_refund",
                "partner_id": partner.id,
                "invoice_date": date(2025, 11, 6),
                "intrastat_country_id": cls.env.ref("base.nl").id,
                "invoice_incoterm_id": False,
            }
        )

        cls.AccountMoveLine.create(
            {
                "move_id": cls.invoice.id,
                "name": "Test Product Line",
                "account_id": cls.env["account.account"].search([], limit=1).id,
                "quantity": 1.0,
                "price_unit": 71.65,
            }
        )

        cls.invoice.action_post()

        cls.intrastat_record = cls.IntrastatMove.new(
            {
                "intrastat_weight": 10.0,
                "intrastat_supplementary_units_amount": 5,
            }
        )
        cls.intrastat_record.move_id = cls.invoice.id
        cls.intrastat_record._compute_defaults_from_move()
        cls.intrastat_record._compute_supplementary_units_code()
        cls.intrastat_record._compute_statistical_value()
        cls.intrastat_record = cls.intrastat_record.create(
            cls.intrastat_record._convert_to_write(cls.intrastat_record._cache)
        )

    def test_default_values(self):
        """_compute_defaults_from_move fills all fields (used by standalone Intrastat form)."""
        invoice = self.invoice
        intrastat_record = self.intrastat_record
        expected_value = sum(invoice.invoice_line_ids.mapped("price_total"))
        self.assertEqual(
            intrastat_record.intrastat_country_code.id, invoice.intrastat_country_id.id
        )
        self.assertAlmostEqual(intrastat_record.intrastat_value, expected_value, places=2)
        self.assertAlmostEqual(
            intrastat_record.intrastat_statistical_value, expected_value, places=2
        )
        intrastat_record = intrastat_record.with_context(force_compute=True)
        self.assertEqual(
            intrastat_record.intrastat_supplementary_units_code,
            intrastat_record.intrastat_commodity_code.supplementary_unit,
        )

    def test_parent_onchange_fills_value(self):
        """Inline tab: parent onchange fills intrastat_value from invoice_line price_total."""
        from odoo.tests import Form

        # Use a fresh invoice so no existing intrastat lines consume the remaining value
        partner = self.invoice.partner_id
        invoice = self.AccountMove.create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "invoice_date": self.invoice.invoice_date,
                "intrastat_country_id": self.invoice.intrastat_country_id.id,
            }
        )
        self.AccountMoveLine.create(
            {
                "move_id": invoice.id,
                "name": "Test Product Line",
                "account_id": self.env["account.account"].search([], limit=1).id,
                "quantity": 1.0,
                "price_unit": 71.65,
            }
        )
        invoice.action_post()
        expected = sum(invoice.invoice_line_ids.mapped("price_total"))
        self.assertGreater(expected, 0, f"Precondition: price_total must be > 0, got {expected}")
        with Form(invoice) as f:
            with f.xx_intrastat_line_ids.new() as line:
                value_after_add = line.intrastat_value
                line.intrastat_supplementary_units_amount = 1
        self.assertAlmostEqual(
            value_after_add,
            expected,
            places=2,
            msg=f"Expected {expected}, got {value_after_add}",
        )

    def test_parent_onchange_vendor_bill_no_date(self):
        """Vendor bill without date: amount_total=0 but price_total gives the correct value."""
        from odoo.tests import Form

        partner = self.invoice.partner_id
        bill = self.AccountMove.create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "invoice_date": False,
                "intrastat_country_id": self.invoice.intrastat_country_id.id,
            }
        )
        self.AccountMoveLine.create(
            {
                "move_id": bill.id,
                "name": "Test Purchase Line",
                "account_id": self.env["account.account"].search([], limit=1).id,
                "price_unit": 115.0,
                "quantity": 1.0,
            }
        )
        expected = sum(bill.invoice_line_ids.mapped("price_total"))
        self.assertGreater(expected, 0, "Precondition: invoice_line price_total must be > 0")
        with Form(bill) as f:
            with f.xx_intrastat_line_ids.new() as line:
                value_after_add = line.intrastat_value
                line.intrastat_supplementary_units_amount = 1
        self.assertAlmostEqual(
            value_after_add,
            expected,
            places=2,
            msg=f"Expected {expected} from price_total, got {value_after_add}",
        )

    def _parse_export_xml(self, xml_content):
        ns = {"ns": "http://www.onegate.eu/2010-01-01"}
        root = etree.parse(BytesIO(xml_content)).getroot()
        items = root.xpath("//ns:Item", namespaces=ns)
        report = root.xpath("//ns:Report", namespaces=ns)[0]
        data = root.xpath("//ns:Data", namespaces=ns)[0]
        return root, report, data, items, ns

    def test_export_xml_standard(self):
        xml_content = self.intrastat_record.get_export_xml(declaration_type="standard")
        root, report, data, items, ns = self._parse_export_xml(xml_content)

        self.assertEqual(report.attrib["code"], "EX19S")
        self.assertEqual(data.attrib["form"], "EXF19S")

        self.assertEqual(len(items), 1)
        dims = {dim.attrib["prop"]: dim.text for dim in items[0].xpath("ns:Dim", namespaces=ns)}

        self.assertEqual(dims.get("EXTRF"), "29")
        self.assertEqual(dims.get("EXCNT"), "NL")
        self.assertEqual(float(dims.get("EXWEIGHT")), 10.0)
        self.assertEqual(float(dims.get("EXTXVAL")), 71.65)
        self.assertEqual(float(dims.get("EXUNITS")), 5.0)

        self.assertNotIn("EXTPC", dims)
        self.assertNotIn("EXDELTRM", dims)
        self.assertNotIn("PARTNERID", dims)
        self.assertNotIn("EXCNTORI", dims)
        self.assertEqual(len(dims), 8)

    def test_export_xml_extended(self):
        xml_content = self.intrastat_record.get_export_xml(declaration_type="extended")
        root, report, data, items, ns = self._parse_export_xml(xml_content)

        self.assertEqual(report.attrib["code"], "EX19E")
        self.assertEqual(data.attrib["form"], "EXF19E")

        self.assertEqual(len(items), 1)
        dims = {dim.attrib["prop"]: dim.text for dim in items[0].xpath("ns:Dim", namespaces=ns)}

        self.assertEqual(dims.get("EXTRF"), "29")
        self.assertEqual(dims.get("EXCNT"), "NL")
        self.assertEqual(float(dims.get("EXWEIGHT")), 10.0)
        self.assertEqual(float(dims.get("EXTXVAL")), 71.65)

        self.assertIn("EXTPC", dims)
        self.assertIn("EXDELTRM", dims)
        self.assertNotIn("PARTNERID", dims)
        self.assertNotIn("EXCNTORI", dims)
        self.assertEqual(len(dims), 10)

    def test_supplementary_units_validation(self):
        with self.assertRaises(ValidationError):
            self.IntrastatMove.create(
                {
                    "move_id": self.invoice.id,
                    "intrastat_code_id": self.intrastat_codes["transaction"].id,
                    "intrastat_commodity_code": self.intrastat_codes["commodity"].id,
                    "intrastat_country_code": self.env.ref("base.nl").id,
                    "intrastat_supplementary_units_code": "p/st",
                    "intrastat_supplementary_units_amount": 0,
                    "intrastat_weight": 5.0,
                    "intrastat_value": 100.0,
                    "intrastat_statistical_value": 100.0,
                }
            )

    def test_default_get_sets_transport_and_incoterm(self):
        """default_get fills transport and incoterm when defaults are configured."""
        self.intrastat_codes["transport"].write({"xx_default_transport": True})
        incoterm = self.env["account.incoterms"].create(
            {"name": "Test Incoterm", "code": "TST", "xx_default_incoterm": True}
        )
        defaults = self.AccountMove.with_context(default_move_type="in_invoice").default_get(
            ["move_type", "intrastat_transport_mode_id", "invoice_incoterm_id"]
        )
        self.assertEqual(
            defaults.get("intrastat_transport_mode_id"), self.intrastat_codes["transport"].id
        )
        self.assertEqual(defaults.get("invoice_incoterm_id"), incoterm.id)

    def test_intrastat_required_true(self):
        """intrastat_required returns True for a cross-border EU invoice when region is set."""
        company = self.env.company
        company.intrastat_region_id = self.intrastat_codes["region"].id
        company.country_id = self.env.ref("base.be")
        partner = self.env["res.partner"].create(
            {"name": "EU Partner", "country_id": self.env.ref("base.nl").id}
        )
        invoice = self.AccountMove.create({"move_type": "in_invoice", "partner_id": partner.id})
        self.assertTrue(invoice.intrastat_required())

    def test_intrastat_required_false_same_country(self):
        """intrastat_required returns False when partner is in the same country as company."""
        company = self.env.company
        company.intrastat_region_id = self.intrastat_codes["region"].id
        company.country_id = self.env.ref("base.be")
        partner = self.env["res.partner"].create(
            {"name": "BE Partner", "country_id": self.env.ref("base.be").id}
        )
        invoice = self.AccountMove.create({"move_type": "in_invoice", "partner_id": partner.id})
        self.assertFalse(invoice.intrastat_required())

    def test_action_post_warning_then_retry(self):
        """action_post warns on first post with no intrastat lines; retrying posts the invoice."""
        company = self.env.company
        company.intrastat_region_id = self.intrastat_codes["region"].id
        company.country_id = self.env.ref("base.be")
        partner = self.env["res.partner"].create(
            {"name": "EU Partner", "country_id": self.env.ref("base.nl").id}
        )
        invoice = self.AccountMove.create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "invoice_date": date(2025, 11, 6),
            }
        )
        self.AccountMoveLine.create(
            {
                "move_id": invoice.id,
                "name": "Test Line",
                "account_id": self.env["account.account"].search([], limit=1).id,
                "quantity": 1.0,
                "price_unit": 100.0,
            }
        )
        result = invoice.action_post()
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("tag"), "display_notification")
        self.assertTrue(invoice.xx_ignore_intrastat_warning)
        self.assertEqual(invoice.state, "draft")
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")

    def test_compute_defaults_no_weight_or_units_and_zero_remaining(self):
        """_compute_defaults_from_move handles zero weight/units and zero remaining value."""
        record = self.IntrastatMove.new({})
        record.move_id = self.invoice.id
        record._compute_defaults_from_move()
        # intrastat_record already consumes the full invoice value → remaining = 0
        self.assertEqual(record.intrastat_value, 0.0)
        self.assertEqual(record.intrastat_statistical_value, 0.0)
        # weight and units default to 0 when not provided
        self.assertEqual(record.intrastat_weight, 0.0)
        self.assertEqual(record.intrastat_supplementary_units_amount, 0)
