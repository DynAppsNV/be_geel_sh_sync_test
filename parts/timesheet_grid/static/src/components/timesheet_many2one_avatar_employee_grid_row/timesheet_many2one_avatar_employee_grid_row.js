import { Component, onWillStart } from "@odoo/owl";

import { user } from "@web/core/user";
import { registry } from "@web/core/registry";
import { Many2OneGridRow, many2OneGridRow } from "@web_grid/components/many2one_grid_row/many2one_grid_row";
import { EmployeeOvertimeIndication } from "../employee_overtime_indication/employee_overtime_indication";
import { useTimesheetOvertimeProps } from "../../hooks/useTimesheetOvertimeProps";
import { TimesheetGridMany2OneGridRow } from "../timesheet_grid_many2one/timesheet_grid_many2one_field";
import { AvatarCardEmployeePopover } from "@hr/components/avatar_card_employee/avatar_card_employee_popover";
import { usePopover } from "@web/core/popover/popover_hook";


export class TimesheetMany2OneAvatarEmployeeGridRow extends Component {
    static template = "timesheet_grid.TimesheetMany2OneAvatarEmployeeGridRow";

    static components = {
        Many2OneGridRow,
        EmployeeOvertimeIndication,
    };

    static props = {
        ...TimesheetGridMany2OneGridRow.props,
    };

    setup() {
        super.setup(...arguments);
        this.employeeOvertimeProps = useTimesheetOvertimeProps();
        this.avatarCard = usePopover(AvatarCardEmployeePopover);

        /* Before the component starts, check if the current user belongs to the HR user group.
        This information is used to determine the appropriate relation for the component.*/
        onWillStart(async () => {
            this.isHrUser = await user.hasGroup("hr.group_hr_user");
        });
    }

    // Chooses employee data visibility based on user role.
    get relation() {
        return this.isHrUser ? "hr.employee" : "hr.employee.public";
    }

    get many2OneProps() {
        return Object.fromEntries(
            Object.entries(this.props).filter(
                ([key,]) => key !== "classNames" && key in this.constructor.components.Many2OneGridRow.props
            )
        );
    }

    get resId() {
        return this.value && this.value[0];
    }

    get displayName() {
        return this.value ? this.value[1] : "";
    }

    get value() {
        return 'value' in this.props ? this.props.value : this.props.row.initialRecordValues[this.props.name];
    }

    get timesheetOvertimeProps() {
        const { units_to_work, uom, worked_hours } = this.employeeOvertimeProps.props;
        return {
            allocated_hours: units_to_work,
            uom,
            worked_hours,
        };
    }

    openCard(ev) {
        if (this.env.isSmall) {
            return;
        }
        const target = ev.currentTarget;
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(target, {
                id: this.resId,
            });
        }
    }
}

export const timesheetMany2OneAvatarEmployeeGridRow = {
    ...many2OneGridRow,
    component: TimesheetMany2OneAvatarEmployeeGridRow,
};

registry
    .category("grid_components")
    .add("timesheet_many2one_avatar_employee", timesheetMany2OneAvatarEmployeeGridRow);
