from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestAccountAccount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_1 = cls.env["account.account"].create(
            {"name": "Test Account 1", "code": "1234"}
        )
        cls.account_2 = cls.env["account.account"].create(
            {"name": "Test Account 2", "code": "5678"}
        )
        cls.env["account.move"].create(
            {
                "line_ids": [
                    Command.create(
                        {
                            "name": "Test Move Line 1",
                            "account_id": cls.account_1.id,
                            "debit": 100.0,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Test Move Line 1",
                            "account_id": cls.account_1.id,
                            "credit": 100.0,
                        }
                    ),
                ]
            }
        )

    def test_archive_account(self):
        with self.assertRaisesRegex(
            UserError, "You cannot perform this action on an account that contains journal items."
        ):
            self.account_1.active = False
        self.account_1.name = "Test Account 1 - Updated"
        self.account_2.active = False
