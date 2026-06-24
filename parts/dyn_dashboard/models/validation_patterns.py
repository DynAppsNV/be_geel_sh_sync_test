import re

from odoo import api, fields, models

REPLACE_PATTERNS = [
    ["&", "_"],
    ["[@a-zA-Z]", "A"],
    ["[#0-9]", "9"],
]


class DynDashboardValidationPatterns(models.Model):
    _name = "xx.dashboard.validation.patterns"
    _description = "DynApps Dashboard Validation Patterns"

    pattern_type = fields.Char("Type of validation")
    country_id = fields.Many2one("res.country")
    validation_rule = fields.Char()
    pattern = fields.Char("Validation Pattern")

    @api.onchange("validation_rule")
    def onchange_validation_rule(self):
        if self.validation_rule:
            rule = self.validation_rule
            for pattern, repl in REPLACE_PATTERNS:
                rule = re.sub(pattern, repl, rule)
            self.pattern = rule
