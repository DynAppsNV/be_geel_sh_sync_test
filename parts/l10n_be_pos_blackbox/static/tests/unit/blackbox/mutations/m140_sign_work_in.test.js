import { test, expect, describe } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    setupPosBlackboxEnv,
    waitForDelayedCalls,
    waitForUnawaitedCalls,
    expectGeneralProperties,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { mountWithCleanup, getMockEnv } from "@web/../tests/web_test_helpers";
import { OpeningControlPopup } from "@point_of_sale/app/components/popups/opening_control_popup/opening_control_popup";

definePosModels();

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/m140_sign_work_in.json' for an example request
describe("sign_work_in", () => {
    test("data generation", async () => {
        const { promise, resolver } = waitForDelayedCalls();
        const store = await setupPosBlackboxEnv(
            async (mockRequest) => {
                const body = await mockRequest.json();
                if (body.operationName === "M140_signWorkIn") {
                    resolver(body.variables.data);
                }
            },
            { setupCashier: false }
        );
        await store.blackbox.signWorkIn.sign(store.models, "1234567890");
        const workIn = await promise;
        // Check general properties
        expectGeneralProperties(workIn, { ticketMedium: "NONE" });
    });

    test("called when opening register, setting & resetting cashier", async () => {
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
        store.data.write("pos.config", [store.session.config_id.id], { module_pos_hr: false });

        const env = getMockEnv();
        const comp = await mountWithCleanup(OpeningControlPopup, {
            props: { close: () => {} },
            env: {
                ...env,
                dialogData: {},
            },
        });
        expect(store.session.l10n_be_users_clocked_ids).toBeEmpty();

        // First work in
        await comp.confirm();
        expect(workInCalls).toBe(1);
        expect(workOutCalls).toBe(0);
        expect(store.session.l10n_be_users_clocked_ids).not.toBeEmpty();

        const user = store.getCashier();
        store.setCashier(user); // Setting same user should do nothing
        await waitForUnawaitedCalls(() => expect(workInCalls).toBe(1));
        await waitForUnawaitedCalls(() => expect(workOutCalls).toBe(0));

        // Reset cashier (should work out)
        store.resetCashier();
        await waitForUnawaitedCalls(() => expect(workInCalls).toBe(1));
        await waitForUnawaitedCalls(() => expect(workOutCalls).toBe(1));

        store.setCashier(user); // Setting same user again (work in)
        await waitForUnawaitedCalls(() => expect(workInCalls).toBe(2));
        await waitForUnawaitedCalls(() => expect(workOutCalls).toBe(1));
    });
});
