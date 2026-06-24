# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from . import wizard


def _account_reports_post_init(env):
    env.ref('account_reports.ir_cron_generate_account_return')._trigger()

    companies = env['res.company'].search([])
    return_types = env['account.return.type'].search([])

    for company in companies:
        for return_type in return_types.with_company(company):
            return_type.deadline_periodicity = return_type.deadline_periodicity or return_type.default_deadline_periodicity
            return_type.deadline_start_date = return_type.deadline_start_date or return_type.default_deadline_start_date

    for company in env['res.company'].search([('chart_template', '!=', False)], order='parent_path'):
        ChartTemplate = env['account.chart.template'].with_company(company)
        # Set up the tax returns journal after the CoA was already installed.
        ChartTemplate._load_data({
            'account.journal': ChartTemplate._get_account_reports_journal(company.chart_template),
            'res.company': ChartTemplate._get_account_reports_res_company(company.chart_template),
        })
