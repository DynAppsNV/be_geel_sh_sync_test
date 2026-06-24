from odoo.tests.common import TransactionCase


class TestIrUiView(TransactionCase):
    def test_dyn_dashboard_view_type(self):
        """Test that 'dyn_dashboard' is a valid view type and _get_view_info is updated."""
        # Check if dyn_dashboard is in the selection of the type field
        view_type_selection = self.env["ir.ui.view"]._fields["type"].selection
        self.assertIn(("dyn_dashboard", "DynApps Dashboard"), view_type_selection)

        # Check _get_view_info
        view_info = self.env["ir.ui.view"]._get_view_info()
        self.assertIn("dyn_dashboard", view_info)
        self.assertEqual(
            view_info["dyn_dashboard"], {"icon": "oi oi-search", "multi_record": False}
        )

    def test_create_dyn_dashboard_view(self):
        """Test creating a view with type 'dyn_dashboard'."""
        view = self.env["ir.ui.view"].create(
            {
                "name": "Test Dyn Dashboard View",
                "model": "res.partner",
                "type": "dyn_dashboard",
                "arch": "<dyn_dashboard/>",
            }
        )
        self.assertEqual(view.type, "dyn_dashboard")
