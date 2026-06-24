import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

async function _isBelgianCompany({ searchModel, model }) {
    if (searchModel.resModel !== "hr.employee" || !model?.root?.resId) {
        return false;
    }
    const currentCompanyId = searchModel.context.allowed_company_ids?.[0];
    if (!currentCompanyId) {
        return false;
    }
    const currentCompany = (
        await searchModel.orm.read(
            "res.company",
            [currentCompanyId],
            ["country_code"]
        )
    )[0];
    return currentCompany?.country_code === "BE";
}

export class WorkingScheduleEmployeeMenu extends Component {
    static template = "l10n_be_hr_payroll.WorkingScheduleEmployeeMenu";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.actionService = useService("action");
    }

    async onClick() {
        const resId = this.env.model.root.resId;
        await this.actionService.doAction(
            "l10n_be_hr_payroll.action_employee_working_schedule_change_request",
            {
                additionalContext: {
                    active_id: resId,
                    active_ids: [resId],
                    active_model: 'hr.employee',
                },
            }
        );
    }
}

registry.category("cogMenu").add(
    "working-schedule-employee-cog",
    {
        Component: WorkingScheduleEmployeeMenu,
        groupNumber: 40,
        isDisplayed: _isBelgianCompany,
    },
    { sequence: 2 }
);
