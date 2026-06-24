# Part of Odoo. See LICENSE file for full copyright and licensing details.

PERCENTAGE_ANALYTIC_DIGITS = 6


def _set_percentage_analytic_precision(env):
    """Raise the "Percentage Analytic" decimal precision to 6.

    Analytic distribution percentages are rounded to this precision server-side in
    analytic.mixin._sanitize_values() on every create/write. The Odoo default is 2,
    which truncates e.g. 0.8325% -> 0.83% and makes the per-line amount drift
    (9.99 -> 9.96 on a 1200 balance).

    The amount/percentage/amount round-trip the widget performs has a resolution of
    balance * 10**-(digits + 2), so cent-exact amounts are only guaranteed while that
    step stays <= EUR 0.01, i.e. balance <= EUR 10_000 at 4 digits but <= EUR 1_000_000
    at 6. 4 digits still drifted a cent on mid-size balances (RA-111: EUR 5,761.06 on a
    EUR 14,402.67 line snapped to EUR 5,761.05 and spawned a 0.0001% / EUR 0.01 line).
    6 digits covers every realistic journal item and matches the precision Odoo's own
    enterprise Winbooks import wizard sets for the same amount-derived scenario.

    The decimal.precision record (analytic.decimal_percentage_analytic) is
    noupdate="1", so a declarative <record> override is silently skipped on both
    install and upgrade. It has to be written imperatively, which is why this lives
    in a hook (fresh installs) and a migration (existing databases).
    """
    precision = env.ref("analytic.decimal_percentage_analytic", raise_if_not_found=False)
    if precision and precision.digits < PERCENTAGE_ANALYTIC_DIGITS:
        precision.digits = PERCENTAGE_ANALYTIC_DIGITS


def post_init_hook(env):
    _set_percentage_analytic_precision(env)
