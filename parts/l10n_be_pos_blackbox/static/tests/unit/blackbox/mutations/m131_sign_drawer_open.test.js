import { test, expect, describe } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    setupPosBlackboxEnv,
    expectGeneralProperties,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { mountWithCleanup, getMockEnv } from "@web/../tests/web_test_helpers";
import { OpeningControlPopup } from "@point_of_sale/app/components/popups/opening_control_popup/opening_control_popup";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";

definePosModels();

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/m131_sign_drawer_open.json' for an example request
describe("sign_drawer_open", () => {
    test("data generation", async () => {
        const store = await setupPosBlackboxEnv();
        const result = await store.blackbox.signDrawerOpen.sign(store.models, "1234567890");
        const response = result.formatted;
        expectGeneralProperties(response, { ticketMedium: "NONE" });
    });

    test("called at right time", async () => {
        let blackboxIsCalled = false;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M131_signDrawerOpen") {
                blackboxIsCalled = true;
            }
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        const env = getMockEnv();
        await getFilledOrder(store);
        const comp = await mountWithCleanup(OpeningControlPopup, {
            props: { close: () => {} },
            env: {
                ...env,
                dialogData: {},
            },
        });
        await comp.openDetailsPopup();
        expect(blackboxIsCalled).toBe(true);
    });
});
