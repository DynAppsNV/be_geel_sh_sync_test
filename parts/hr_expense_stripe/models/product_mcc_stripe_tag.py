import random
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


# https://docs.stripe.com/connect/setting-mcc#list
class ProductMCCSTripeTag(models.Model):
    _name = 'product.mcc.stripe.tag'
    _description = "Stripe MCC Tag"
    _order = 'code'

    name = fields.Char(string="Name", required=True, translate=True)
    stripe_name = fields.Char(string="Stripe Name", required=True, readonly=True)
    code = fields.Char(string="Code", required=True, readonly=True, size=9, copy=False, index='btree')
    product_id = fields.Many2one(
        string="Expense Category to use",
        comodel_name='product.product',
        domain=[('can_be_expensed', '=', True), ('standard_price', '=', 0)],
        company_dependent=True,
    )
    product_name = fields.Char(related='product_id.name', string="Product Name")
    color = fields.Integer(
        string="Color Index",
        default=lambda self: random.randint(0, 9),
        store=True,
    )

    _constraint_code_unique = models.Constraint(
        definition='unique(code)',
        message="The code of the MCC tag must be unique!",
    )

    @api.constrains('product_id')
    def _check_no_cost(self):
        price_precision = self.env['decimal.precision'].precision_get("Product Price")
        for product in self.product_id:
            if round(product.standard_price, int(price_precision)) != 0:
                raise ValidationError(_("To be used by Expense cards, the product '%(name)s' must have a cost of 0.00", name=product.name))

    @api.constrains('code')
    def _check_code_format(self):
        pattern = re.compile(r'^\d{4}(-\d{4})?$')
        for mcc in self:
            if not pattern.match(mcc.code):
                raise ValidationError(self.env._(
                    "The MCC code '%(code)s' is not valid. It must be either a 4-digit code or a range in the format 'XXXX-XXXX'.",
                    code=mcc.code,
                ))

    def _mcc_is_in_range(self, mcc_code):
        if not mcc_code:
            return False
        mcc_ranges = self.filtered(lambda mcc: '-' in mcc.code)
        if mcc_code in set((self - mcc_ranges).mapped('code')):
            return True
        mcc_code = int(mcc_code)
        for mcc in mcc_ranges:
            start, end = (int(code) for code in mcc.code.split('-'))
            if start <= mcc_code <= end:
                return True
        return False

    def write(self, vals):
        if ('code' in vals or 'stripe_name' in vals) and not self.has_access('create'):
            raise UserError(_(
                "Only administrators can change the code or the stripe technical name of a MCC."
            ))
        return super().write(vals)
