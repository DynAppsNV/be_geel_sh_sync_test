import { test, expect, describe } from "@odoo/hoot";
import {
    expectTransactionLine,
    generatePosOrder,
    setupPosBlackboxEnv,
    expectGeneralProperties,
    expectFinancial,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/m171_is_training.json' for an example request
describe("isTraining", () => {
    test("data generation", async () => {
        let request = null;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M110_signSale") {
                request = body.variables;
            }
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        const models = store.models;
        const config = models["pos.config"].get(1);

        config.l10n_be_training_mode = true;

        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const burger = models["product.product"].find((p) => p.name === "Burger of the Chef");
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
                    product_id: burger.id,
                    qty: 1,
                    price_unit: burger.lst_price,
                    tax_ids: burger.taxes_id.map((t) => t.id),
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

        const response = await store.blackbox.signSale.sign(order, "1234567890");
        const input = response.formatted;
        const transactions = input.transaction.transactionLines;
        const financials = input.financials;

        // Check general properties
        expectGeneralProperties(input, { order: order, ticketMedium: "DIGITAL" });
        expect(transactions).toHaveLength(2);
        expect(input.transaction.transactionTotal).toBe(52);
        expect(request.training).toBe(true);

        // Check transaction details - Dry Martini
        expectTransactionLine(transactions[0], martini, 2, "PIECE", 12, "A", "SINGLE_PRODUCT");

        // Check transaction details - Burger of the Chef
        expectTransactionLine(transactions[1], burger, 1, "PIECE", 28, "B", "SINGLE_PRODUCT");

        // Check payment details
        expectFinancial(financials[0], "Cash", "PAYMENT", 52, "CASH");
    });
});
