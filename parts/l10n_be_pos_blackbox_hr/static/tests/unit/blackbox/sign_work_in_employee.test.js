import { test, expect, describe } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    setupPosBlackboxEnv,
    waitForUnawaitedCalls,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { LoginScreen } from "@point_of_sale/app/screens/login_screen/login_screen";
import { mountWithCleanup, getMockEnv } from "@web/../tests/web_test_helpers";
import { click, waitFor } from "@odoo/hoot-dom";
import { OpeningControlPopup } from "@point_of_sale/app/components/popups/opening_control_popup/opening_control_popup";

definePosModels();

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/m140_sign_work_in.json' for an example request
describe("sign_work_in", () => {
    test("called from login screen (closed session)", async () => {
        let workInCalls = 0,
            workOutCalls = 0;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            const operation = body.operationName;
            if (operation === "M140_signWorkIn") {
                workInCalls++;
            } else if (operation === "M141_signWorkOut") {
                workOutCalls++;
            }
        };
        const store = await setupPosBlackboxEnv(expectRequest, { setupCashier: false });
        store.session.state = "closed";
        store.session.l10n_be_employees_clocked_ids = [];

        const env = getMockEnv();
        await mountWithCleanup(LoginScreen, {
            env: {
                ...env,
                dialogData: {},
            },
        });
        await click("button.open-register-btn");

        await waitFor("button.select-cashier");
        await click("button.select-cashier");

        await waitFor("button.selection-item:contains('Fake Employee')");
        await click("button.selection-item:contains('Fake Employee')");

        const comp = await mountWithCleanup(OpeningControlPopup, {
            props: { close: () => {} },
            env: {
                ...env,
                dialogData: {},
            },
        });
        await comp.confirm();
        expect(workInCalls).toBe(1);
        expect(workOutCalls).toBe(0);
    });
    test("called at right time (set & reset cashier)", async () => {
        let workInCalls = 0,
            workOutCalls = 0;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            const operation = body.operationName;
            if (operation === "M140_signWorkIn") {
                workInCalls++;
            } else if (operation === "M141_signWorkOut") {
                workOutCalls++;
            }
        };

        const store = await setupPosBlackboxEnv(expectRequest, { setupCashier: false });

        const fakeEmp = store.models["hr.employee"].get(2);
        const fakeEmpBasic = store.models["hr.employee"].get(3);
        expect(store.session.l10n_be_employees_clocked_ids.length).toBe(0);
        await waitForUnawaitedCalls(() => expect(workInCalls).toBe(0));
        await waitForUnawaitedCalls(() => expect(workOutCalls).toBe(0));
        // First work in
        store.setCashier(fakeEmp);
        await waitForUnawaitedCalls(() => expect(workInCalls).toBe(1));
        await waitForUnawaitedCalls(() => expect(workOutCalls).toBe(0));
        // Refresh session (should now contains the cashier as clocked in)
        await store.data.read("pos.session", [store.session.id]);
        expect(store.session.l10n_be_employees_clocked_ids.length).toBe(1);

        store.setCashier(fakeEmp); // Setting same user should do nothing
        await waitForUnawaitedCalls(() => expect(workInCalls).toBe(1));
        await waitForUnawaitedCalls(() => expect(workOutCalls).toBe(0));
        await store.data.read("pos.session", [store.session.id]);
        expect(store.session.l10n_be_employees_clocked_ids.length).toBe(1);

        store.setCashier(fakeEmpBasic); // Work in another employee
        await waitForUnawaitedCalls(() => expect(workInCalls).toBe(2));
        await waitForUnawaitedCalls(() => expect(workOutCalls).toBe(0));
        await store.data.read("pos.session", [store.session.id]);
        expect(store.session.l10n_be_employees_clocked_ids.length).toBe(2);

        store.resetCashier(); // Should work out the current cashier
        await waitForUnawaitedCalls(() => expect(workInCalls).toBe(2));
        await waitForUnawaitedCalls(() => expect(workOutCalls).toBe(1));
        await store.data.read("pos.session", [store.session.id]);
        expect(store.session.l10n_be_employees_clocked_ids.length).toBe(1);

        await store.workOutAllCashiers(); // Should work out remaining cashier
        expect(workInCalls).toBe(2);
        expect(workOutCalls).toBe(2);
        await store.data.read("pos.session", [store.session.id]);
        expect(store.session.l10n_be_employees_clocked_ids.length).toBe(0);
    });
});
