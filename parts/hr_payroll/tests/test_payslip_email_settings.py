# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.addons.hr_payroll.tests.common import TestPayslipBase
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestPayslipEmailSettings(TestPayslipBase):
    """
    Tests for the payslip generate-and-send trigger stored in ir.config_parameter
    under the key 'hr_payroll.payslip_generate_and_send_trigger'.

    Three modes are exercised for both single and batch payslips:
    on_confirmed: single payslip generates PDF directly on validation;
                  batch payslips are queued for the cron.
    on_paid: all payslips are queued for the cron when marked as paid.
    never: never generates automatically; sending is fully manual.

    An absent parameter must fall back to 'on_confirmed' to preserve the
    historical behaviour of the module before this setting was introduced.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Second employee needed for batch tests, minimal setup mirrors richard_emp.
        cls.employee_b = cls.env['hr.employee'].create({
            'name': 'Employee B',
            'date_version': date(2018, 1, 1),
            'contract_date_start': date(2018, 1, 1),
            'wage': 3000.0,
            'structure_type_id': cls.structure_type.id,
        })

    def setUp(self):
        super().setUp()
        # One fresh payslip per employee for October 2025, recreated each test.
        self.payslip_a = self._mk_payslip(self.richard_emp)
        self.payslip_b = self._mk_payslip(self.employee_b)

    def _mk_payslip(self, employee):
        """ Create a draft payslip covering October 2025 for the given employee. """
        return self.env['hr.payslip'].create({
            'name': f'Payslip {employee.name}',
            'employee_id': employee.id,
            'version_id': employee.version_ids[0].id,
            'date_from': date(2025, 10, 1),
            'date_to': date(2025, 10, 31),
        })

    def _set_trigger(self, value):
        """ Persist the given trigger mode to ir.config_parameter. """
        self.env['ir.config_parameter'].sudo().set_param('hr_payroll.payslip_generate_and_send_trigger', value)

    def _validate(self, payslips):
        """ Validate payslips with the PDF-generation context active. """
        payslips.with_context(payslip_generate_pdf=True).action_validate()

    def get_payslip_attachments(self, payslip):
        """ Return attachments linked to the given payslip. """
        return self.env['ir.attachment'].search([
            ('res_model', '=', payslip._name),
            ('res_id', '=', payslip.id),
        ])

    def test_single_on_confirmed(self):
        """
        Single payslip with on_confirmed: PDF must be generated directly on validation.
        Marking it as paid must not trigger another PDF.
        """
        self._set_trigger('on_confirmed')
        self._validate(self.payslip_a)
        self.assertEqual(
            len(self.get_payslip_attachments(self.payslip_a)),
            1,
            'on_confirmed single: validation must generate the PDF directly',
        )
        self.payslip_a.action_payslip_paid()
        self.assertEqual(
            len(self.get_payslip_attachments(self.payslip_a)),
            1,
            'on_confirmed single: payment must not generate another PDF',
        )

    def test_single_on_paid(self):
        """
        Single payslip with on_paid: validation must not generate or queue anything.
        Marking it as paid must queue the payslip for the cron.
        """
        self._set_trigger('on_paid')
        self._validate(self.payslip_a)
        self.assertFalse(
            self.payslip_a.queued_for_pdf,
            'on_paid single: validation must not queue the payslip',
        )
        self.payslip_a.action_payslip_paid()
        self.assertTrue(
            self.payslip_a.queued_for_pdf,
            'on_paid single: payment must queue the payslip for PDF generation',
        )

    def test_single_never(self):
        """
        Test 'never' mode: neither validation nor payment should set queued_for_pdf.
        The HR manager is expected to trigger PDF generation manually.
        """
        self._set_trigger('never')
        self._validate(self.payslip_a)
        self.assertFalse(
            self.payslip_a.queued_for_pdf,
            'never: validation must not queue the payslip',
        )
        self.payslip_a.action_payslip_paid()
        self.assertFalse(
            self.payslip_a.queued_for_pdf,
            'never: payment must not queue the payslip',
        )

    def test_multi_on_confirmed(self):
        """
        Batch payslips with on_confirmed: all must be queued on validation.
        Subsequent payment must not re-queue any of them.
        """
        self._set_trigger('on_confirmed')
        payslips = self.payslip_a | self.payslip_b
        self._validate(payslips)
        self.assertTrue(
            all(p.queued_for_pdf for p in payslips),
            'on_confirmed batch: every payslip must be queued after validation',
        )
        payslips._cron_generate_pdf()
        payslips.action_payslip_paid()
        self.assertFalse(
            any(p.queued_for_pdf for p in payslips),
            'on_confirmed batch: payment must not re-queue any payslip',
        )

    def test_multi_on_paid(self):
        """
        Batch payslips with on_paid: validation must not queue any.
        Batch payment must queue them all.
        """
        self._set_trigger('on_paid')
        payslips = self.payslip_a | self.payslip_b
        self._validate(payslips)
        self.assertFalse(
            any(p.queued_for_pdf for p in payslips),
            'on_paid batch: validation must not queue any payslip',
        )
        payslips.action_payslip_paid()
        self.assertTrue(
            all(p.queued_for_pdf for p in payslips),
            'on_paid batch: payment must queue every payslip',
        )

    def test_multi_never(self):
        """
        Batch payslips with never: neither validation nor payment must touch queued_for_pdf.
        """
        self._set_trigger('never')
        payslips = self.payslip_a | self.payslip_b
        self._validate(payslips)
        self.assertFalse(
            any(p.queued_for_pdf for p in payslips),
            'never batch: validation must not queue any payslip',
        )
        payslips.action_payslip_paid()
        self.assertFalse(
            any(p.queued_for_pdf for p in payslips),
            'never batch: payment must not queue any payslip',
        )

    def test_default_fallback(self):
        """
        When ir.config_parameter has no entry for the trigger key,
        _get_payslip_send_trigger() must fall back to 'on_confirmed', so a single
        payslip generates its PDF directly on validation.
        """
        # Remove the parameter entirely to simulate a fresh install.
        self.env['ir.config_parameter'].sudo().search(
            [('key', '=', 'hr_payroll.payslip_generate_and_send_trigger')]
        ).unlink()
        self._validate(self.payslip_a)
        self.assertEqual(
            len(self.get_payslip_attachments(self.payslip_a)),
            1,
            'absent parameter: single payslip PDF generated directly (on_confirmed fallback)',
        )
