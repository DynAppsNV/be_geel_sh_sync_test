import { test, expect, describe } from "@odoo/hoot";
import {
    expectTransactionLine,
    generatePosOrder,
    setupPosBlackboxEnv,
    waitForDelayedCalls,
    expectGeneralProperties,
    payOrder,
    getComboOrder,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";

definePosModels();

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/uc220_sign_sale_lign_price_change.json' for an example request
describe("sign_sale_lign_price_change", () => {
    test("data generation", async () => {
        const { promise, resolver } = waitForDelayedCalls();
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M110_signSale") {
                resolver(body.variables.data);
            }
        });
        const models = store.models;
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const burger = models["product.product"].find((p) => p.name === "Burger of the Chef");
        const order = generatePosOrder(
            models,
            [
                {
                    product_id: martini.id,
                    qty: 1,
                    price_unit: martini.lst_price,
                    tax_ids: martini.taxes_id.map((t) => t.id),
                },
                {
                    product_id: burger.id,
                    qty: 1,
                    price_unit: burger.lst_price,
                    tax_ids: burger.taxes_id.map((t) => t.id),
                    discount: 50,
                },
            ],
            [
                {
                    amount: 26,
                    reference: "Test Payment",
                    uuid: "fake-uuid-1234",
                    payment_method_id: models["pos.payment.method"].find((m) => m.name === "Cash")
                        .id,
                },
            ]
        );

        await store.blackbox.signSale.sign(order, "1234567890");
        const input = await promise;
        const transactions = input.transaction.transactionLines;
        const financials = input.financials;

        // Check general properties
        expectGeneralProperties(input, {
            order: order,
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });
        expect(transactions).toHaveLength(2);
        expect(input.transaction.transactionTotal).toBe(26); // With discount applied

        expectTransactionLine(transactions[0], martini, 1, "PIECE", 12, "A", "SINGLE_PRODUCT");
        expect(transactions[0].lineTotal).toBe(12);
        expectTransactionLine(transactions[1], burger, 1, "PIECE", 28, "B", "SINGLE_PRODUCT");
        expect(transactions[1].lineTotal).toBe(14); // After 50% discount

        expect(transactions[0].mainProduct.vats[0].priceChanges).toHaveLength(0);
        expect(transactions[1].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transactions[1].mainProduct.vats[0].priceChanges[0].scope).toBe("LINE");
        expect(transactions[1].mainProduct.vats[0].priceChanges[0].type).toBe("PUBLIC");
        expect(transactions[1].mainProduct.vats[0].priceChanges[0].name).toBe("DISCOUNT_50P");
        expect(transactions[1].mainProduct.vats[0].priceChanges[0].amount).toBeCloseTo(-14);

        // Check payment details
        expect(financials[0].name).toBe("Cash");
        expect(financials[0].amountType).toBe("PAYMENT");
        expect(financials[0].amount).toBe(26);
        expect(financials[0].inputMethod).toBe("MANUAL");
        expect(financials[0].id).not.toBeEmpty();
    });

    test("called at right time with price changes", async () => {
        let blackboxIsCalled = false;
        let request = null;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M110_signSale") {
                blackboxIsCalled = true;
                request = body.variables.data;
            }
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        const order = await getFilledOrder(store);
        const comp = await mountWithCleanup(OrderSummary, {});
        await comp.setLinePrice(order.lines[0], 999);
        payOrder(store, order);
        await store.syncAllOrders();
        expect(blackboxIsCalled).toBe(true);

        const transLines = request.transaction.transactionLines;
        expect(transLines[0].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].scope).toBe("LINE");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].name).toBe("UNIT_PRICE_CHANGE");
        expect(transLines[1].mainProduct.vats[0].priceChanges).toHaveLength(0);

        expectGeneralProperties(request, {
            order: order,
            employeeId: "97121722222",
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });
        expect(order.displayPrice).toBe(request.transaction.transactionTotal);
    });

    test("called at right time with discount", async () => {
        let blackboxIsCalled = false;
        let request = null;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M110_signSale") {
                blackboxIsCalled = true;
                request = body.variables.data;
            }
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        const order = await getFilledOrder(store);
        store.setDiscountFromUI(order.lines[0], 50);
        payOrder(store, order);
        await store.syncAllOrders();
        expect(blackboxIsCalled).toBe(true);

        const transLines = request.transaction.transactionLines;
        expect(transLines[0].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].scope).toBe("LINE");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].name).toBe("DISCOUNT_50P");
        expect(transLines[1].mainProduct.vats[0].priceChanges).toHaveLength(0);

        expectGeneralProperties(request, {
            order: order,
            employeeId: "97121722222",
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });
        expect(order.displayPrice).toBe(request.transaction.transactionTotal);
    });

    test("called at right time with discount and manual price change", async () => {
        let blackboxIsCalled = false;
        let request = null;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M110_signSale") {
                blackboxIsCalled = true;
                request = body.variables.data;
            }
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        const order = await getFilledOrder(store);
        const comp = await mountWithCleanup(OrderSummary, {});
        await comp.setLinePrice(order.lines[0], 1000);
        store.setDiscountFromUI(order.lines[0], 50);
        payOrder(store, order);
        await store.syncAllOrders();
        expect(blackboxIsCalled).toBe(true);

        const transLines = request.transaction.transactionLines;

        expect(transLines[0].mainProduct.vats[0].priceChanges).toHaveLength(2);
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].scope).toBe("LINE");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].name).toBe("UNIT_PRICE_CHANGE");

        expect(transLines[0].mainProduct.vats[0].priceChanges[1].scope).toBe("LINE");
        expect(transLines[0].mainProduct.vats[0].priceChanges[1].name).toBe("DISCOUNT_50P");
        expect(transLines[1].mainProduct.vats[0].priceChanges).toHaveLength(0);

        expectGeneralProperties(request, {
            order: order,
            employeeId: "97121722222",
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });
        expect(order.displayPrice).toBe(request.transaction.transactionTotal);
    });

    test("called at right time with global discount", async () => {
        let blackboxIsCalled = false;
        let request = null;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M110_signSale") {
                blackboxIsCalled = true;
                request = body.variables.data;
            }
        };

        // Normal order
        const store = await setupPosBlackboxEnv(expectRequest);
        const order = await getFilledOrder(store);
        await store.applyDiscount(10, order);
        payOrder(store, order);
        await store.syncAllOrders();
        expect(blackboxIsCalled).toBe(true);

        const transLines = request.transaction.transactionLines;
        expect(transLines[0].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].scope).toBe("EVENT");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].name).toBe("GLOBAL_DISCOUNT_10P");
        expect(transLines[1].mainProduct.vats[0].priceChanges).toHaveLength(1);

        expectGeneralProperties(request, {
            order: order,
            employeeId: "97121722222",
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });
        expect(order.displayPrice).toBe(request.transaction.transactionTotal);
    });

    test("called at right time with global discount and combo product", async () => {
        let blackboxIsCalled = false;
        let request = null;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M110_signSale") {
                blackboxIsCalled = true;
                request = body.variables.data;
            }
        };
        const store = await setupPosBlackboxEnv(expectRequest);

        const comboOrder = getComboOrder(store, false);
        await store.applyDiscount(10, comboOrder);
        payOrder(store, comboOrder);
        await store.syncAllOrders();
        expect(blackboxIsCalled).toBe(true);

        const comboTransLines = request.transaction.transactionLines;
        const priceChanges = comboTransLines[0].subProducts[0].vats[0].priceChanges;
        expect(priceChanges).toHaveLength(2);
        expect(priceChanges[0].scope).toBe("LINE");
        expect(priceChanges[0].name).toBe("MENU_DISCOUNT");
        expect(priceChanges[1].scope).toBe("EVENT");
        expect(priceChanges[1].name).toBe("GLOBAL_DISCOUNT_10P");
        expectGeneralProperties(request, {
            order: comboOrder,
            employeeId: "97121722222",
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });
    });

    test("called at right time with manual price change, line discount and global discount", async () => {
        let blackboxIsCalled = false;
        let request = null;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M110_signSale") {
                blackboxIsCalled = true;
                request = body.variables.data;
            }
        };

        const store = await setupPosBlackboxEnv(expectRequest);
        const order = await getFilledOrder(store);
        const comp = await mountWithCleanup(OrderSummary, {});
        await comp.setLinePrice(order.lines[0], 1000);
        store.setDiscountFromUI(order.lines[0], 50);
        await store.applyDiscount(50, order);
        payOrder(store, order);
        await store.syncAllOrders();
        expect(blackboxIsCalled).toBe(true);

        const transLines = request.transaction.transactionLines;

        //First order line (with global discount, line discount and global discount)
        expect(transLines[0].mainProduct.vats[0].priceChanges).toHaveLength(3);

        expect(transLines[0].mainProduct.vats[0].priceChanges[0].scope).toBe("EVENT");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].name).toBe("GLOBAL_DISCOUNT_50P");

        expect(transLines[0].mainProduct.vats[0].priceChanges[1].scope).toBe("LINE");
        expect(transLines[0].mainProduct.vats[0].priceChanges[1].name).toBe("UNIT_PRICE_CHANGE");

        expect(transLines[0].mainProduct.vats[0].priceChanges[2].scope).toBe("LINE");
        expect(transLines[0].mainProduct.vats[0].priceChanges[2].name).toBe("DISCOUNT_50P");

        //Second order line (with only global discount)
        expect(transLines[1].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transLines[1].mainProduct.vats[0].priceChanges[0].scope).toBe("EVENT");
        expect(transLines[1].mainProduct.vats[0].priceChanges[0].name).toBe("GLOBAL_DISCOUNT_50P");

        expectGeneralProperties(request, {
            order: order,
            employeeId: "97121722222",
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });
        expect(order.displayPrice).toBe(request.transaction.transactionTotal);
    });
});
