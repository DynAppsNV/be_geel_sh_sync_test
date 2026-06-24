import { fields, defineModels } from "@web/../tests/web_test_helpers";
import { hrTimesheetModels } from "@hr_timesheet/../tests/hr_timesheet_models";
import { defineTimesheetModels } from "@timesheet_grid/../tests/hr_timesheet_models";
import { helpdeskModels } from "@helpdesk/../tests/helpdesk_test_helpers";
import { HrEmployee } from "@hr/../tests/mock_server/mock_models/hr_employee";

export class HelpdeskTeam extends helpdeskModels.HelpdeskTeam {
    _name = "helpdesk.team";

    project_id = fields.Many2one({
        relation: "project.project",
    });
}

export class HelpdeskTicket extends helpdeskModels.HelpdeskTicket {
    _name = "helpdesk.ticket";

    project_id = fields.Many2one({
        relation: "project.project",
    });
}

export class HRTimesheet extends hrTimesheetModels.HRTimesheet {
    helpdesk_ticket_id = fields.Many2one({
        relation: "helpdesk.ticket",
    });
    has_helpdesk_team = fields.Boolean();
}

export class HelpdeskTicketReportAnalysis extends helpdeskModels.HelpdeskTicketReportAnalysis {
    employee_id = fields.Many2one({ relation: "hr.employee" });
}

hrTimesheetModels.HRTimesheet = HRTimesheet;
helpdeskModels.HelpdeskTicket = HelpdeskTicket;
helpdeskModels.HelpdeskTeam = HelpdeskTeam;
helpdeskModels.HelpdeskTicketReportAnalysis = HelpdeskTicketReportAnalysis;
helpdeskModels.HelpdeskTicket._views = {
    "list": `<list><field name="name"/></list>`,
};

export function defineHelpdeskTimesheetModels() {
    defineModels({
        ...helpdeskModels,
        HrEmployee,
    });
    defineTimesheetModels();
}
