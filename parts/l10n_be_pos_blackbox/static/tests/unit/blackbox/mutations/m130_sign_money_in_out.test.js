import { test, expect, describe } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    setupPosBlackboxEnv,
    expectGeneralProperties,
    expectFinancial,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { mountWithCleanup, getMockEnv } from "@web/../tests/web_test_helpers";
import { CashMovePopup } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_popup";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";

definePosModels();

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/m130_sign_money_in_out.json' for an example request
describe("sign_money_in_out", () => {
    test("data generation", async () => {
        const store = await setupPosBlackboxEnv();
        const result = await store.blackbox.signMoneyInOut.sign(store.models, "1234567890", {
            amount: 100,
            name: "Cash In",
        });
        const cashIn = result.formatted;
        // Check general properties
        expectGeneralProperties(cashIn, { ticketMedium: "DIGITAL" });

        const financials = cashIn.financials;
        expect(financials[0].amount).toBe(100);
        expect(financials[0].name).toBe("Cash In");
        expect(financials[0].amountType).toBe("MONEY_IN_OUT");
        expect(financials[0].inputMethod).toBe("MANUAL");

        const result2 = await store.blackbox.signMoneyInOut.sign(store.models, "1234567890", {
            amount: -100,
            name: "Cash Out",
        });
        const cashOut = result2.formatted;
        const financialsOut = cashOut.financials;
        expectFinancial(financialsOut[0], "Cash Out", "MONEY_IN_OUT", -100, "CASH");
    });

    test("called at right time", async () => {
        let blackboxIsCalled = false;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M130_signMoneyInOut") {
                blackboxIsCalled = true;
            }
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        const env = getMockEnv();
        await getFilledOrder(store);
        const comp = await mountWithCleanup(CashMovePopup, {
            props: { close: () => {} },
            env: {
                ...env,
                dialogData: {},
            },
        });
        comp.state.amount = "100";
        comp.state.type = "in";
        await comp.confirm();
        expect(blackboxIsCalled).toBe(true);
    });
});
