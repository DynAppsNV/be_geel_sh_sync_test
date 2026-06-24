import { test, describe } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    setupPosBlackboxEnv,
    waitForDelayedCalls,
    expectGeneralProperties,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";

definePosModels();

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/m141_sign_work_out.json' for an example request
describe("sign_work_out", () => {
    test("data generation", async () => {
        const { promise, resolver } = waitForDelayedCalls();
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M141_signWorkOut") {
                resolver(body.variables.data);
            }
        });
        await store.blackbox.signWorkOut.sign(store.models, "1234567890");
        const workOut = await promise;

        // Check general properties
        expectGeneralProperties(workOut, { ticketMedium: "NONE" });
    });
});
