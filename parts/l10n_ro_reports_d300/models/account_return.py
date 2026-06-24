from odoo import _, fields, models


class AccountReturn(models.Model):
    _inherit = "account.return"

    l10n_ro_fiscal_address = fields.Char(
        string="Fiscal Domicile Address",
        help="Adresă domiciliu fiscal: Fiscal address of the organization (if not specified, the address set on company will be used).",
    )
    l10n_ro_declarant_name = fields.Char()
    l10n_ro_declarant_surname = fields.Char()
    l10n_ro_declarant_role = fields.Char()
    l10n_ro_bank_name = fields.Char()
    l10n_ro_bank_account = fields.Char()
    l10n_ro_caen_code = fields.Char()
    l10n_ro_post_audit_filing = fields.Boolean()
    l10n_ro_return_period = fields.Selection(
        selection=[
            ("L", "Monthly (L)"),
            ("T", "Quarterly (T)"),
            ("S", "Biannual (S)"),
            ("A", "Annual (A)"),
        ],
    )
    l10n_ro_pro_rata = fields.Float()
    l10n_ro_request_refund = fields.Boolean()
    l10n_ro_filed_by_representative = fields.Boolean()
    l10n_ro_simplified_internal = fields.Boolean()
    l10n_ro_sale_cereals = fields.Boolean()
    l10n_ro_sale_mobile_phones = fields.Boolean()
    l10n_ro_sale_integrated_circuits = fields.Boolean()
    l10n_ro_sale_consoles_tablets_laptops = fields.Boolean()

    def action_validate(self, bypass_failing_tests=False):
        # OVERRIDE
        if self.type_external_id == "l10n_ro_reports.ro_tax_return_type":
            self._review_checks(bypass_failing_tests)
            new_wizard = self.env["l10n_ro.d300.lock.wizard"].create([{"return_id": self.id}])
            return {
                "type": "ir.actions.act_window",
                "name": _("Lock"),
                "view_mode": "form",
                "res_model": "l10n_ro.d300.lock.wizard",
                "target": "new",
                "res_id": new_wizard.id,
                "views": [[self.env.ref("l10n_ro_reports_d300.vat_return_lock_wizard_form").id, "form"]],
                "context": {
                    "dialog_size": "large",
                },
            }
        return super().action_validate(bypass_failing_tests)

    def action_submit(self):
        if self.type_external_id == "l10n_ro_reports.ro_tax_return_type":
            return self.env["l10n_ro.d300.submission.wizard"]._open_submission_wizard(self)
        return super().action_submit()
