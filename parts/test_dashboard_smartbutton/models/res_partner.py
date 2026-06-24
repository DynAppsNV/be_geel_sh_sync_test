# Copyright 2020 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models


class Partner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "dashboard.smart.button.mixin"]
