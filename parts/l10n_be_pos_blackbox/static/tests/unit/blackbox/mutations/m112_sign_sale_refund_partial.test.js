import { test, expect, describe } from "@odoo/hoot";
import {
    expectTransactionLine,
    generatePosOrder,
    setupPosBlackboxEnv,
    expectGeneralProperties,
    expectFinancial,
    setOrderFdmSignature,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";

definePosModels();

// enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/m112_sign_sale_refund_partial.json
describe("sign_sale_refund_partial", () => {
    test("data generation", async () => {
        const store = await setupPosBlackboxEnv();
        const models = store.models;
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const coca = models["product.product"].find((p) => p.name === "Coca Cola");

        // First create an initial order to be refunded
        const initOrder = generatePosOrder(
            models,
            [
                {
                    product_id: martini.id,
                    qty: 2,
                    price_unit: martini.lst_price,
                    tax_ids: martini.taxes_id.map((t) => t.id),
                },
                {
                    product_id: coca.id,
                    qty: 1,
                    price_unit: coca.lst_price,
                    tax_ids: coca.taxes_id.map((t) => t.id),
                },
            ],
            [
                {
                    amount: 27.04,
                    reference: "Test Payment",
                    uuid: "fake-uuid-1234",
                    payment_method_id: models["pos.payment.method"].find((m) => m.name === "Cash")
                        .id,
                },
            ],
            { orderId: 2 }
        );
        setOrderFdmSignature(initOrder);

        const refundOrder = generatePosOrder(
            models,
            [
                {
                    product_id: martini.id,
                    qty: -1,
                    price_unit: martini.lst_price,
                    tax_ids: martini.taxes_id.map((t) => t.id),
                },
            ],
            [
                {
                    amount: -12,
                    reference: "Test Payment",
                    uuid: "fake-uuid-1234",
                    payment_method_id: models["pos.payment.method"].find((m) => m.name === "Cash")
                        .id,
                },
            ],
            { refundedOrderId: initOrder.id }
        );

        const response = await store.blackbox.signSaleRefundPartial.sign(refundOrder, "1234567890");
        const input = response.formatted;
        const transactions = input.transaction.transactionLines;
        const financials = input.financials;

        // Check general properties
        expectGeneralProperties(input, { order: refundOrder, ticketMedium: "DIGITAL" });
        expect(transactions).toHaveLength(1);
        expect(input.transaction.transactionTotal).toBe(-12);

        // Check transaction details - Dry Martini
        const martiniTrc = transactions[0];
        expectTransactionLine(
            martiniTrc,
            martini,
            -1,
            "PIECE",
            12,
            "A",
            "SINGLE_PRODUCT",
            "REFUND"
        );

        // Check payment details
        expectFinancial(financials[0], "Cash", "PAYMENT", -12, "CASH");
        // Check FDM reference
        const fdmRef = input.fdmRef;
        expect(fdmRef.eventCounter).toBe(1);
        expect(fdmRef.eventLabel).toBe("N");
        expect(fdmRef.fdmId).toBe("1234567890");
        expect(fdmRef.totalCounter).toBe(100);
    });

    test("called at right time", async () => {
        let blackboxIsCalled = false;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M112_signSale_RefundPartial") {
                blackboxIsCalled = true;
            }
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        const order = await getFilledOrder(store, {}, true, true);
        setOrderFdmSignature(order.refunded_order_id);
        // Make it partial refund
        order.lines[0].delete();

        // Creating a paid order should trigger the blackbox signSale when syncing orders
        await store.syncAllOrders();
        expect(blackboxIsCalled).toBe(true);
    });
});
