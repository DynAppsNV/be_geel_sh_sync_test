{
    'name': 'Belgian Payroll - Holiday Attest Fix',
    'version': '1.0',
    'category': 'Human Resources/Payroll',
    'description': """
        This module patches the 'hr.payslip.employee.depature.holiday.attests.time.off.line'
        transient model to use Floats instead of Integers.

        This prevents rounding errors when employees have half-days (0.5)
        in their leave allocations or taken leaves.
    """,
    'depends': ['l10n_be_hr_payroll'],
    'author': 'Odoo S.A.',
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
