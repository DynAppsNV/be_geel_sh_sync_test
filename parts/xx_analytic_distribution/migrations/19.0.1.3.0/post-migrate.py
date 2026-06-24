# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import SUPERUSER_ID, api

from odoo.addons.xx_analytic_distribution.hooks import _set_percentage_analytic_precision


def migrate(cr, version):
    """Raise "Percentage Analytic" precision to 6 on existing databases (RA-111).

    post_init_hook only runs on a fresh install; existing databases reach the new
    precision through this migration when the module version is bumped to 19.0.1.3.0.
    The hook guards on `digits < 6`, so this is idempotent and safely upgrades the
    previous 4-digit value (or a Winbooks-import DB already at 6).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    _set_percentage_analytic_precision(env)
