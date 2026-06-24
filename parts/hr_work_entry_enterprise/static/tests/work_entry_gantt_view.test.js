import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { findComponent, makeMockServer, mountView, contains } from "@web/../tests/web_test_helpers";
import { WorkEntriesGanttController } from "@hr_work_entry_enterprise/work_entries_gantt_controller";
import { defineHrWorkEntryModels } from "@hr_work_entry/../tests/hr_work_entry_test_helpers";
import { getCell, hoverCell, getGridContent } from "@web_gantt/../tests/web_gantt_test_helpers";
const { DateTime } = luxon;

describe.current.tags("desktop");
defineHrWorkEntryModels();

beforeEach(() => {
    mockDate("2025-01-01 12:00:00", +0);
});

async function selectBlock({ sourceCell, targetCell }) {
    await hoverCell(sourceCell);
    const { drop, moveTo } = await contains(sourceCell).drag();
    await moveTo(targetCell);
    await animationFrame();
    await drop();
    await animationFrame();
}

function getGanttController(view) {
    return findComponent(view, (c) => c instanceof WorkEntriesGanttController);
}

test("multi-selection quick buttons deduplicate favorites", async () => {
    const { env } = await makeMockServer();
    const [type] = env["hr.work.entry.type"].create([
        {
            name: "MyType",
        },
    ]);
    // two work entries of the same type on two different days; this mimics
    // the situation where formattedReadGroup returns two groups with identical
    // work_entry_type_id but different create_date:day values.
    env["hr.work.entry"].create([
        {
            name: "e1",
            employee_id: 100,
            work_entry_type_id: type,
            date: "2025-01-01",
            create_date: "2025-01-01",
        },
        {
            name: "e2",
            employee_id: 100,
            work_entry_type_id: type,
            date: "2025-01-02",
            create_date: "2025-01-02",
        },
    ]);

    const gantt = await mountView({
        type: "gantt",
        resModel: "hr.work.entry",
    });
    const controller = getGanttController(gantt);
    await controller.model._fetchUserFavoritesWorkEntries();
    // favorites should be deduplicated
    // only one work entry type should appear in the list.
    expect(controller.model.userFavoritesWorkEntries).toHaveLength(1, {
        message: "userFavoritesWorkEntries list must contain just one type",
    });
});

test("multi-selection buttons hidden when no employees", async () => {
    await mountView({
        type: "gantt",
        resModel: "hr.work.entry",
    });

    await selectBlock({
        sourceCell: getCell("01", "January 2025"),
        targetCell: getCell("06", "January 2025"),
    });
    await animationFrame();

    expect(".o_multi_selection_buttons").toHaveCount(0, {
        message: "Buttons must be hidden when no employees exist",
    });
});

test("multi-selection buttons visible when employees exist", async () => {
    const { env } = await makeMockServer();
    env["hr.work.entry"].create([
        {
            name: "Test Work Entry",
            employee_id: 100,
            work_entry_type_id: false,
            date: "2025-01-01",
            create_date: "2025-01-01",
            duration: 120,
        },
    ]);

    const gantt = await mountView({
        type: "gantt",
        resModel: "hr.work.entry",
    });
    const controller = getGanttController(gantt);
    const cellInfo = {
        rowId: JSON.stringify([{ employee_id: [100, "Richard"] }]),
        start: DateTime.fromISO("2025-01-01"),
        stop: DateTime.fromISO("2025-01-02"),
    };
    await controller.model.multiCreateRecords(
        { record: { getChanges: () => ({ name: "Test New Work Entry", employee_id: 100 }) } },
        [cellInfo]
    );
    const rowTitle = getGridContent().rows[0].title;
    await selectBlock({
        sourceCell: getCell("01", "January 2025", rowTitle),
        targetCell: getCell("02", "January 2025", rowTitle),
    });
    await animationFrame();

    expect(".o_selection_box").toHaveText("2\nselected");
    expect(".o_multi_selection_buttons").toHaveCount(1, {
        message: "Buttons must be visible when employees exist",
    });
});
