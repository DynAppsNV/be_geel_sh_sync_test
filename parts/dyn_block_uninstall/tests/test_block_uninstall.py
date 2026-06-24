from odoo.exceptions import UserError
from odoo.tests import common


class TestDynBlockUninstall(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ir_module_model = cls.env["ir.module.module"]
        cls.module_dyn_block_uninstall = cls.ir_module_model.search(
            [("name", "=", "dyn_block_uninstall")]
        )
        cls.module_base = cls.ir_module_model.search([("name", "=", "base")])
        cls.module_base_address_extended = cls.ir_module_model.search(
            [("name", "=", "base_address_extended")]
        )

    def _install_module_base_address_extended(self):
        self.module_base_address_extended.button_install()
        self.ir_module_model.update_list()

    def test_get_values_from_terp(self):
        self.assertTrue(
            self.ir_module_model.get_values_from_terp(
                self.ir_module_model.get_module_info(self.module_dyn_block_uninstall.name)
            )["dyn_required"]
        )
        self.assertFalse(
            self.ir_module_model.get_values_from_terp(
                self.ir_module_model.get_module_info(self.module_base.name)
            )["dyn_required"]
        )
        self._install_module_base_address_extended()
        self.assertFalse(
            self.ir_module_model.get_values_from_terp(
                self.ir_module_model.get_module_info(self.module_base_address_extended.name)
            )["dyn_required"]
        )

    def test_dyn_required_dependency(self):
        self.assertTrue(self.module_dyn_block_uninstall.dyn_required_dependency)
        self.assertTrue(self.module_base.dyn_required_dependency)
        self._install_module_base_address_extended()
        self.assertFalse(self.module_base_address_extended.dyn_required_dependency)

    def test_button_uninstall(self):
        with self.assertRaisesRegex(
            UserError, "Uninstalling a Dynapps required module is not possible."
        ):
            self.module_dyn_block_uninstall.button_uninstall()
        with self.assertRaisesRegex(
            UserError, "Uninstalling a Dynapps required module is not possible."
        ):
            self.module_base.button_uninstall()
        self._install_module_base_address_extended()
        with self.assertRaisesRegex(
            UserError, "One or more of the selected modules have already been uninstalled"
        ):
            self.module_base_address_extended.button_uninstall()

    def test_module_uninstall(self):
        with self.assertRaisesRegex(
            UserError, "Uninstalling a Dynapps required module is not possible."
        ):
            self.module_dyn_block_uninstall.module_uninstall()
        with self.assertRaisesRegex(
            UserError, "Uninstalling a Dynapps required module is not possible."
        ):
            self.module_base.module_uninstall()
        self._install_module_base_address_extended()
        self.module_base_address_extended.module_uninstall()
