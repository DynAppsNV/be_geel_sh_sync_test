import { test, expect, describe } from "@odoo/hoot";
import {
    expectTransactionLine,
    generatePosOrder,
    setupPosBlackboxEnv,
    expectGeneralProperties,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

definePosModels();

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/m123_sign_pre_bill.json' for an example request
describe("sign_pre_bill", () => {
    test("data generation", async () => {
        const store = await setupPosBlackboxEnv();
        const models = store.models;
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const tapas = models["product.product"].find((p) => p.name === "Tapas variation");
        const order = generatePosOrder(
            models,
            [
                {
                    product_id: martini.id,
                    qty: 2,
                    price_unit: martini.lst_price,
                    tax_ids: martini.taxes_id.map((t) => t.id),
                },
                {
                    product_id: tapas.id,
                    qty: 4,
                    price_unit: tapas.lst_price,
                    tax_ids: tapas.taxes_id.map((t) => t.id),
                },
            ],
            [
                {
                    amount: 52,
                    reference: "Test Payment",
                    uuid: "fake-uuid-1234",
                    payment_method_id: models["pos.payment.method"].find((m) => m.name === "Cash")
                        .id,
                },
            ]
        );

        const response = await store.blackbox.signPreBill.sign(order, "1234567890");
        const input = response.formatted;
        const transactions = input.transaction.transactionLines;
        const financials = input.financials;

        // Check general properties
        expectGeneralProperties(input, { order: order, ticketMedium: "DIGITAL" });
        expect(transactions).toHaveLength(2);
        expect(input.transaction.transactionTotal).toBe(37.36);
        expect(input.costCenter).not.toBeEmpty();

        // Check transaction details - Dry Martini
        expectTransactionLine(transactions[0], martini, 2, "PIECE", 12, "A", "SINGLE_PRODUCT");

        // Check transaction details - Tapas variation
        expectTransactionLine(transactions[1], tapas, 4, "PIECE", 3.34, "B", "SINGLE_PRODUCT");

        // Check payment details
        expect(financials).toBeEmpty();
    });

    test("called at right time", async () => {
        let blackboxIsCalled = false;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M123_signPreBill") {
                blackboxIsCalled = true;
            }
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        const order = await getFilledOrder(store);
        store.setOrder(order);
        const comp = await mountWithCleanup(ControlButtons, {});
        await comp.clickPrintBill();
        expect(blackboxIsCalled).toBe(true);
    });
});
