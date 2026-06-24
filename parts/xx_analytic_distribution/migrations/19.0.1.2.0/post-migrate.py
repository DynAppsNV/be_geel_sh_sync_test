# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import SUPERUSER_ID, api

from odoo.addons.xx_analytic_distribution.hooks import _set_percentage_analytic_precision


def migrate(cr, version):
    """Apply the bumped "Percentage Analytic" precision to existing databases.

    post_init_hook only runs on a fresh install; existing databases reach the new
    precision through this migration when the module version is bumped to 19.0.1.2.0.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    _set_percentage_analytic_precision(env)
