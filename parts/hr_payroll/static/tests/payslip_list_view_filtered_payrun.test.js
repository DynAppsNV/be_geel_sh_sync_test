import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    findComponent,
    models,
    mountView,
    mockService
} from "@web/../tests/web_test_helpers";
import { Record } from "@web/model/record";
import { defineHrPayrollModels } from "@hr_payroll/../tests/hr_payroll_test_helpers";
import { HrPayslip } from "@hr_payroll/../tests/mock_server/mock_models/hr_payslip";
import { PayslipListController } from "@hr_payroll/views/payslip_list/hr_payslip_list_controller";
import { PayRunCard } from "@hr_payroll/components/payrun_card/payrun_card";

class TestW2Form extends models.Model {
    _name = "test.w2.form";
    payslip_ids = fields.Many2many({ relation: "hr.payslip", string: "Payslips" });
    _records = [{ id: 1, payslip_ids: [] }];
}

describe.current.tags("desktop");
defineHrPayrollModels();
defineModels([TestW2Form]);

beforeEach(() => {
    mockDate("2025-01-01 12:00:00", +0);
    HrPayslip._records = [];
});

test("Test context of PayRunCard", async () => {
    const view = await mountView({
        type: "list",
        resModel: "hr.payslip",
        context: {
            search_default_payslip_run_id: 1,
        },
    });
    const payslipListController = findComponent(
        view,
        (component) => component instanceof PayslipListController
    );
    const record = findComponent(
        view,
        (component) =>
            component instanceof Record &&
            findComponent(component, (subComponent) => subComponent instanceof PayRunCard)
    );
    expect(record.props.context).toEqual(payslipListController.props.context);
});

test("Test header buttons of payslip list view filtered by payrun", async () => {
    await mountView({
        type: "list",
        resModel: "hr.payslip",
        context: {
            search_default_payslip_run_id: 1,
        },
    });
    expect(".o_control_panel_main_buttons button").toHaveCount(1);
    expect(".o_list_button_add").toHaveText("New");
});

test('Clicking "Create a Payslip" from empty helper opens payslip form', async () => {
    mockService("action", {
        doAction: async (action) => {
            expect.step(action);
        },
    });

    await mountView({
        type: "form",
        resModel: "test.w2.form",
        resId: 1,
        arch: `
            <form>
                <field name="payslip_ids">
                    <list create="false">
                        <field name="employee_id"/>
                    </list>
                </field>
            </form>
        `,
    });
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".o_view_nocontent").toHaveText(/Create a Payslip/);
    await contains('a:contains("Create a Payslip")').click();
    expect.verifySteps(["hr_payroll.action_hr_payslip_new"]);
});
