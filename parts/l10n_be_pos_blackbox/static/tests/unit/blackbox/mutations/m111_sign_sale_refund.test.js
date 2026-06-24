import { test, expect, describe } from "@odoo/hoot";
import {
    expectTransactionLine,
    generatePosOrder,
    setupPosBlackboxEnv,
    expectGeneralProperties,
    expectFinancial,
    setOrderFdmSignature,
    payOrder,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";

definePosModels();

// enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/m111_sign_sale_refund.json
describe("sign_sale_refund", () => {
    test("data generation", async () => {
        const store = await setupPosBlackboxEnv();
        const models = store.models;
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const burger = models["product.product"].find((p) => p.name === "Burger of the Chef");

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
            ],
            { orderId: 2 }
        );
        setOrderFdmSignature(initOrder);

        // Then create the refund order
        const refundOrder = generatePosOrder(
            models,
            [
                {
                    product_id: martini.id,
                    qty: -2,
                    price_unit: martini.lst_price,
                    tax_ids: martini.taxes_id.map((t) => t.id),
                },
                {
                    product_id: burger.id,
                    qty: -1,
                    price_unit: burger.lst_price,
                    tax_ids: burger.taxes_id.map((t) => t.id),
                },
            ],
            [
                {
                    amount: -52,
                    reference: "Test Payment",
                    uuid: "fake-uuid-1234",
                    payment_method_id: models["pos.payment.method"].find((m) => m.name === "Cash")
                        .id,
                },
            ],
            { refundedOrderId: initOrder.id }
        );

        const response = await store.blackbox.signSaleRefund.sign(refundOrder, "1234567890");
        const input = response.formatted;
        const transactions = input.transaction.transactionLines;
        const financials = input.financials;
        // Check general properties
        expectGeneralProperties(input, { order: refundOrder, ticketMedium: "DIGITAL" });
        expect(transactions).toHaveLength(2);
        expect(input.transaction.transactionTotal).toBe(-52);

        // Check transaction details - Dry Martini
        const martiniTrc = transactions[0];
        expectTransactionLine(
            martiniTrc,
            martini,
            -2,
            "PIECE",
            12,
            "A",
            "SINGLE_PRODUCT",
            "REFUND"
        );

        // Check transaction details - Burger of the Chef
        const burgerTrc = transactions[1];
        expectTransactionLine(burgerTrc, burger, -1, "PIECE", 28, "B", "SINGLE_PRODUCT", "REFUND");

        // Check payment details
        expectFinancial(financials[0], "Cash", "PAYMENT", -52, "CASH");

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
            if (body.operationName === "M111_signSale_Refund") {
                blackboxIsCalled = true;
            }
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        const order = await getFilledOrder(store, {}, true, true);
        setOrderFdmSignature(order.refunded_order_id);
        // Creating a paid order should trigger the blackbox signSale when syncing orders
        await store.syncAllOrders();
        expect(blackboxIsCalled).toBe(true);
    });

    test("refund order with tip amount", async () => {
        const store = await setupPosBlackboxEnv();
        const refundOrder = await getFilledOrder(store, {}, false, true); // refund order not paid yet
        setOrderFdmSignature(refundOrder.refunded_order_id);
        expect(refundOrder.priceIncl).toBe(-185);
        const tipProduct = store.models["product.product"].get(1); // Tip product
        await store.addLineToOrder(
            { product_tmpl_id: tipProduct.product_tmpl_id, qty: -1, price_unit: 5 },
            refundOrder
        );

        expect(refundOrder.priceIncl).toBe(-190);
        payOrder(store, refundOrder);
        expect(refundOrder.lines).toHaveLength(3); // 2 products + 1 tip line
        const response = await store.blackbox.signSaleRefund.sign(refundOrder, "1234567890");
        const input = response.formatted;
        const transactions = input.transaction.transactionLines;
        const financials = input.financials;

        // Check general properties
        expectGeneralProperties(input, {
            order: refundOrder,
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });
        expect(transactions).toHaveLength(3); // for refund, tip line is a transaction line
        expectTransactionLine(
            transactions[2],
            tipProduct,
            -1,
            "PIECE",
            1,
            "X",
            "SINGLE_PRODUCT",
            "REFUND"
        );
        expect(input.transaction.transactionTotal).toBe(-190);
        expect(financials).toHaveLength(1); // payment + tip
        expectFinancial(financials[0], "Cash", "PAYMENT", -190, "CASH");
    });
});
