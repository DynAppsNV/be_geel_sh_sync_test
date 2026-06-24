
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.sign.utils.pdf_handling import _get_field_value
from odoo.tools.pdf import NameObject


@tagged('at_install', '-post_install')
class TestPdfHandlingUtils(TransactionCase):

    def test_get_field_value_adobe_bug(self):
        """
        Test that a text field (/Tx) with an appearance state (/AS)
        returns its text value (/V) and does NOT render as a checkbox.
        """
        mock_annot = {
            "/Type": NameObject("/Annot"),
            "/Subtype": NameObject("/Widget"),
            "/FT": NameObject("/Tx"),
            "/AS": NameObject("/N"),
            "/V": "5081",
        }

        # It should return "5081", ignoring the /AS tag completely
        self.assertEqual(_get_field_value(mock_annot), "5081")

    def test_get_field_value_checked_button(self):
        """
        Test that a checked button (/Btn) correctly renders a checkmark.
        """
        mock_annot = {
            "/Type": NameObject("/Annot"),
            "/Subtype": NameObject("/Widget"),
            "/FT": NameObject("/Btn"),
            "/AS": NameObject("/On"),
        }

        # It should return the unicode checkmark
        self.assertEqual(_get_field_value(mock_annot), chr(0x2713))

    def test_get_field_value_unchecked_button(self):
        """
        Test that an unchecked button (/Btn) returns an empty string.
        """
        mock_annot = {
            "/Type": NameObject("/Annot"),
            "/Subtype": NameObject("/Widget"),
            "/FT": NameObject("/Btn"),
            "/AS": NameObject("/Off"),
            "/V": NameObject("/Off"),
        }

        self.assertEqual(_get_field_value(mock_annot), "")

    def test_get_field_value_normal_text(self):
        """
        Test a standard text field without an /AS tag.
        """
        mock_annot = {
            "/Type": NameObject("/Annot"),
            "/Subtype": NameObject("/Widget"),
            "/FT": NameObject("/Tx"),
            "/V": "Standard Text",
        }

        self.assertEqual(_get_field_value(mock_annot), "Standard Text")
