import { test, expect, describe } from "@odoo/hoot";
import {
    expectTransactionLine,
    generatePosOrder,
    setupPosBlackboxEnv,
    waitForDelayedCalls,
    expectGeneralProperties,
    waitForUnawaitedCalls,
    getComboOrder,
    getMultiQtyComboOrder,
    payOrder,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ControlButtonsPopup } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

definePosModels();

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/uc230_sign_sale_correction.json' for an example request
describe("sign_order_correction", () => {
    test("finalizeValidation signs correction with tracked max quantity before payment", async () => {
        let correctionRequest = null;
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M121_signOrder") {
                correctionRequest = body.variables.data;
            }
        });
        const models = store.models;
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const order = generatePosOrder(models, [
            {
                product_id: martini.id,
                qty: 3,
                price_unit: martini.lst_price,
                tax_ids: martini.taxes_id.map((t) => t.id),
            },
        ]);
        const validation = new OrderPaymentValidation({ pos: store, orderUuid: order.uuid });

        order.lines[0].setQuantity(2);

        payOrder(store, order);
        await validation.finalizeValidation();

        const transactions = correctionRequest.transaction.transactionLines;

        expect(correctionRequest).not.toBe(null);
        expectGeneralProperties(correctionRequest, {
            order,
            ticketMedium: "NONE",
            employeeId: "97121722222",
        });
        expect(transactions).toHaveLength(2);
        expectTransactionLine(transactions[0], martini, 3, "PIECE", 12, "A", "SINGLE_PRODUCT");
        expect(transactions[0].lineTotal).toBe(36);
        expectTransactionLine(
            transactions[1],
            martini,
            -1,
            "PIECE",
            12,
            "A",
            "SINGLE_PRODUCT",
            "CORRECTION"
        );
        expect(transactions[1].lineTotal).toBe(-12);
        expect(order.lines[0].uiState.maxQuantity).toBe(order.lines[0].qty);
    });

    test("finalizeValidation signs correction with tracked max unit price before payment", async () => {
        let correctionRequest = null;
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M121_signOrder") {
                correctionRequest = body.variables.data;
            }
        });
        const models = store.models;
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const order = generatePosOrder(models, [
            {
                product_id: martini.id,
                qty: 1,
                price_unit: martini.lst_price,
                tax_ids: martini.taxes_id.map((t) => t.id),
            },
        ]);
        const validation = new OrderPaymentValidation({ pos: store, orderUuid: order.uuid });

        const unitPrice = order.lines[0].price_unit;
        order.lines[0].setUnitPrice(15);
        // Reset the unit price to the original price
        order.lines[0].setUnitPrice(unitPrice);

        payOrder(store, order);
        await validation.finalizeValidation();

        const transactions = correctionRequest.transaction.transactionLines;

        expect(correctionRequest).not.toBe(null);
        expectGeneralProperties(correctionRequest, {
            order,
            ticketMedium: "NONE",
            mustHavePriceChanges: true,
            employeeId: "97121722222",
        });
        expect(transactions).toHaveLength(3);
        expectTransactionLine(transactions[0], martini, 1, "PIECE", 12, "A", "SINGLE_PRODUCT");
        expect(transactions[0].lineTotal).toBe(15);
        expect(transactions[0].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transactions[0].mainProduct.vats[0].priceChanges[0].name).toBe("UNIT_PRICE_CHANGE");

        expectTransactionLine(
            transactions[1],
            martini,
            -1,
            "PIECE",
            12,
            "A",
            "SINGLE_PRODUCT",
            "PRICE_CHANGE"
        );
        expect(transactions[1].lineTotal).toBe(-15);

        expectTransactionLine(transactions[2], martini, 1, "PIECE", 12, "A", "SINGLE_PRODUCT");
        expect(transactions[2].lineTotal).toBe(12);
        expect(transactions[2].mainProduct.vats[0].priceChanges).toHaveLength(0);
        expect(order.lines[0].uiState.maxUnitPrice).toBe(
            order.lines[0].blackboxPriceUnitNoDiscount
        );
    });

    test("finalizeValidation signs correction for a line added then removed before payment", async () => {
        const { promise, resolver } = waitForDelayedCalls();
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M121_signOrder") {
                resolver(body.variables.data);
            }
        });
        const models = store.models;
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const order = generatePosOrder(models, []);
        const validation = new OrderPaymentValidation({ pos: store, orderUuid: order.uuid });

        const addedLine = models["pos.order.line"].create({
            product_id: martini.id,
            qty: 1,
            order_id: order.id,
            price_unit: martini.lst_price,
            tax_ids: martini.taxes_id,
        });

        order.removeOrderline(addedLine);

        payOrder(store, order);
        await validation.finalizeValidation();

        const request = await promise;
        const transactions = request.transaction.transactionLines;

        expectGeneralProperties(request, {
            order,
            ticketMedium: "NONE",
            employeeId: "97121722222",
        });
        expect(transactions).toHaveLength(2);
        expectTransactionLine(transactions[0], martini, 1, "PIECE", 12, "A", "SINGLE_PRODUCT");
        expect(transactions[0].mainProduct.quantity).toBe(1);
        expect(transactions[0].lineTotal).toBe(12);

        expectTransactionLine(
            transactions[1],
            martini,
            -1,
            "PIECE",
            12,
            "A",
            "SINGLE_PRODUCT",
            "CORRECTION"
        );
        expect(transactions[1].mainProduct.quantity).toBe(-1);
        expect(transactions[1].lineTotal).toBe(-12);
    });

    test("data generation", async () => {
        const { promise, resolver } = waitForDelayedCalls();
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M110_signSale" || body.operationName === "M121_signOrder") {
                resolver(body.variables.data);
            }
        });
        const models = store.models;
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        // Create initial order with 3 Dry Martinis, then change quantity to 2
        const order = generatePosOrder(models, [
            {
                product_id: martini.id,
                qty: 3,
                price_unit: martini.lst_price,
                tax_ids: martini.taxes_id.map((t) => t.id),
            },
        ]);
        await store.syncAllOrders();
        order.updateLastTransactionLines();
        order.lines[0].setQuantity(2);

        await store.blackbox.signOrder.sign(order, "1234567890", true);
        const input = await promise;
        const transactions = input.transaction.transactionLines;

        // Check general properties
        expectGeneralProperties(input, { order: order, ticketMedium: "NONE" });
        expect(transactions).toHaveLength(1);
        expectTransactionLine(
            transactions[0],
            martini,
            -1,
            "PIECE",
            12,
            "A",
            "SINGLE_PRODUCT",
            "CORRECTION"
        );
        expect(transactions[0].lineTotal).toBe(-12);
    });

    test("test signOrder correction: new lines, deleted lines: corrected lines", async () => {
        let order = null;
        let signOrderCalledTimes = 0;
        let request = null;
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M121_signOrder") {
                request = body.variables.data;
                order.updateLastTransactionLines();
                signOrderCalledTimes++;
            }
        });
        const models = store.models;
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const chardonnay = models["product.product"].find((p) => p.name === "Chardonnay White");

        // Create initial order with 3 Dry Martinis, then change quantity to 2
        order = generatePosOrder(models, [
            {
                product_id: martini.id,
                qty: 3,
                price_unit: martini.lst_price,
                tax_ids: martini.taxes_id.map((t) => t.id),
            },
        ]);
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(1));
        let transactions = request.transaction.transactionLines; // New lines with 3 martini
        expect(transactions).toHaveLength(1);
        expectGeneralProperties(request, { order: order, ticketMedium: "NONE" });
        expectTransactionLine(transactions[0], martini, 3, "PIECE", 12, "A", "SINGLE_PRODUCT");

        // If we sign again without changing anything, it should not signOrder again
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(1));

        // Add 2 new lines
        await store.addLineToOrder({ product_tmpl_id: chardonnay.id, qty: 2 }, order);
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(2));
        transactions = request.transaction.transactionLines; // New lines with 2 chardonnay
        expect(transactions).toHaveLength(1);
        expectGeneralProperties(request, { order: order, ticketMedium: "NONE" });
        expectTransactionLine(transactions[0], chardonnay, 2, "PIECE", 40, "A", "SINGLE_PRODUCT");

        // If we sign again without changing anything, it should not signOrder again
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(2));

        // Update first line qty to 4
        order.lines[0].setQuantity(4);
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(3));
        transactions = request.transaction.transactionLines; // New line with 1 added martini
        expect(transactions).toHaveLength(1);
        expectGeneralProperties(request, { order: order, ticketMedium: "NONE" });
        expectTransactionLine(transactions[0], martini, 1, "PIECE", 12, "A", "SINGLE_PRODUCT");
        expect(transactions[0].lineTotal).toBe(12);

        // If we sign again without changing anything, it should not signOrder again
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(3));

        // Delete the second line
        order.removeOrderline(order.lines[1]);
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(4));
        transactions = request.transaction.transactionLines; // Deleted line with 2 chardonnay
        expect(transactions).toHaveLength(1);
        expectGeneralProperties(request, { order: order, ticketMedium: "NONE" });
        expectTransactionLine(
            transactions[0],
            chardonnay,
            -2,
            "PIECE",
            40,
            "A",
            "SINGLE_PRODUCT",
            "CORRECTION"
        );

        // If we sign again without changing anything, it should not signOrder again
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(4));
    });

    test("called at right time (when canceling order)", async () => {
        let blackboxIsCalled = false;
        let request = null;
        let order = null;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M121_signOrder") {
                blackboxIsCalled = true;
                request = body.variables.data;
                order.updateLastTransactionLines();
            }
        };
        // Create an order
        const store = await setupPosBlackboxEnv(expectRequest);
        const models = store.models;
        order = await getFilledOrder(store);
        order.updateLastTransactionLines();

        // Now cancel it and check that blackbox is called again
        await mountWithCleanup(ControlButtonsPopup, {
            props: { close: () => {} },
        });
        await contains("button:contains('Cancel Order')").click();
        await contains(".modal-content .btn-primary").click();
        await waitForUnawaitedCalls(() => expect(blackboxIsCalled).toBe(true));

        const transactions = request.transaction.transactionLines;

        // Check general properties
        expectGeneralProperties(request, { employeeId: "97121722222", ticketMedium: "NONE" });
        expect(transactions).toHaveLength(2);
        expect(request.transaction.transactionTotal).toBe(-185);

        const bourgogne = models["product.product"].find((p) => p.name === "Bourgogne Red");
        const chardonnay = models["product.product"].find((p) => p.name === "Chardonnay White");

        expectTransactionLine(transactions[0], bourgogne, -3, "PIECE", 35, "A", "SINGLE_PRODUCT");
        expect(transactions[0].lineTotal).toBe(-105);
        expect(transactions[1].mainProduct.negQuantityReason).toBe("CORRECTION");

        expectTransactionLine(transactions[1], chardonnay, -2, "PIECE", 40, "A", "SINGLE_PRODUCT");
        expect(transactions[1].lineTotal).toBe(-80);
        expect(transactions[1].mainProduct.negQuantityReason).toBe("CORRECTION");
    });

    test("called at right time (when canceling a combo order)", async () => {
        let blackboxIsCalled = false;
        let request = null;
        let order = null;
        const expectRequest = async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M121_signOrder") {
                blackboxIsCalled = true;
                request = body.variables.data;
                order.updateLastTransactionLines();
            }
        };
        // Create an order
        const store = await setupPosBlackboxEnv(expectRequest);
        order = await getComboOrder(store);
        order.updateLastTransactionLines();

        // Now cancel it and check that blackbox is called again
        await mountWithCleanup(ControlButtonsPopup, {
            props: { close: () => {} },
        });
        await contains("button:contains('Cancel Order')").click();
        await contains(".modal-content .btn-primary").click();
        await waitForUnawaitedCalls(() => expect(blackboxIsCalled).toBe(true));

        const transactions = request.transaction.transactionLines;

        // Check general properties
        expectGeneralProperties(request, { employeeId: "97121722222", ticketMedium: "NONE" });
        expect(transactions).toHaveLength(1);
        expect(request.transaction.transactionTotal).toBe(-58);
        expect(request.transaction.transactionLines[0].lineTotal).toBe(-58);
        expect(request.transaction.transactionLines[0].mainProduct.quantity).toBe(-1);
        expect(request.transaction.transactionLines[0].subProducts[0].quantity).toBe(-1);
        expect(request.transaction.transactionLines[0].subProducts[0].negQuantityReason).toBe(
            "CORRECTION"
        );
    });

    test("combo qty change: sub-product quantity corrections (simple)", async () => {
        // All combo sub-lines have base qty=1 per parent unit.
        // parent 1→3: delta=+2, each sub sends +2.
        // parent 3→1: delta=-2, each sub sends -2 (CORRECTION).
        let order = null;
        let signOrderCalledTimes = 0;
        let request = null;
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M121_signOrder") {
                request = body.variables.data;
                order.updateLastTransactionLines();
                signOrderCalledTimes++;
            }
        });

        order = getComboOrder(store); // parent=1, starter=1, burger=1, wine=1
        const parentLine = order.lines.find((l) => !l.combo_parent_id && l.combo_line_ids.length);

        // Initial sign: parent qty=1, each sub-line qty=1
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(1));
        let transactions = request.transaction.transactionLines;
        expect(transactions).toHaveLength(1);
        expectGeneralProperties(request, { order: order, ticketMedium: "NONE" });
        expect(transactions[0].mainProduct.quantity).toBe(1);
        expect(transactions[0].subProducts[0].quantity).toBe(1); // starter
        expect(transactions[0].subProducts[1].quantity).toBe(1); // burger
        expect(transactions[0].subProducts[2].quantity).toBe(1); // wine

        // If we sign again without changes, no new request
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(1));

        // Increase parent qty 1→5: delta=+4
        // After setQuantity(5): parent=5, each sub=5. subQty=(5/5)*4=4 each.
        parentLine.setQuantity(5, false);
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(2));
        transactions = request.transaction.transactionLines;
        expect(transactions).toHaveLength(1);
        expectGeneralProperties(request, { order: order, ticketMedium: "NONE" });
        expect(transactions[0].mainProduct.quantity).toBe(4); // delta
        expect(transactions[0].subProducts[0].quantity).toBe(4); // (5/5)*4
        expect(transactions[0].subProducts[1].quantity).toBe(4);
        expect(transactions[0].subProducts[2].quantity).toBe(4);

        // If we sign again without changes, no new request
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(2));

        // Decrease parent qty 5→3: delta=-2, correction
        // After setQuantity(3): parent=3, each sub=3. subQty=(3/3)*-2= -2 → negated -2 each.
        parentLine.setQuantity(3, false);
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(3));
        transactions = request.transaction.transactionLines;
        expect(transactions).toHaveLength(1);
        expectGeneralProperties(request, { order: order, ticketMedium: "NONE" });
        expect(transactions[0].mainProduct.quantity).toBe(-2);
        expect(transactions[0].mainProduct.negQuantityReason).toBe("CORRECTION");
        expect(transactions[0].subProducts[0].quantity).toBe(-2); // (1/1)*2, negated
        expect(transactions[0].subProducts[0].negQuantityReason).toBe("CORRECTION");
        expect(transactions[0].subProducts[1].quantity).toBe(-2);
        expect(transactions[0].subProducts[1].negQuantityReason).toBe("CORRECTION");
        expect(transactions[0].subProducts[2].quantity).toBe(-2);
        expect(transactions[0].subProducts[2].negQuantityReason).toBe("CORRECTION");
    });

    test("multi-qty combo: sub-product quantity corrections", async () => {
        // Sub-lines have individual base quantities per parent unit: starter=2, burger=1, wine=3.
        // parent 1→5: delta=+4. subQty: starter=(10/5)*4=8, burger=(5/5)*4=4, wine=(15/5)*4=12.
        // parent 5→3: delta=-2. subQty: starter=(6/3)*2=4, burger=(3/3)*2=2, wine=(9/3)*2=6 → CORRECTION.
        let order = null;
        let signOrderCalledTimes = 0;
        let request = null;
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M121_signOrder") {
                request = body.variables.data;
                order.updateLastTransactionLines();
                signOrderCalledTimes++;
            }
        });

        order = getMultiQtyComboOrder(store); // parent=1, starter=2, wine=3, burger=1
        const parentLine = order.lines.find((l) => !l.combo_parent_id && l.combo_line_ids.length);

        // Initial sign: parent=1, starter=2, wine=3, burger=1. lineTotal=58
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(1));
        let transactions = request.transaction.transactionLines;
        expect(transactions).toHaveLength(1);
        expectGeneralProperties(request, { order: order, ticketMedium: "NONE" });
        expect(transactions[0].mainProduct.quantity).toBe(1);
        expect(transactions[0].subProducts[0].quantity).toBe(2); // starter base qty
        expect(transactions[0].subProducts[1].quantity).toBe(3); // wine base qty
        expect(transactions[0].subProducts[2].quantity).toBe(1); // burger base qty
        expect(transactions[0].lineTotal).toBe(58);

        // If we sign again without changes, no new request
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(1));

        // Increase parent qty 1→5: delta=+4
        // After setQuantity(5): parent=5, starter=10, wine=15, burger=5.
        // subQty: starter=(10/5)*4=8, wine=(15/5)*4=12, burger=(5/5)*4=4. lineTotal=232
        parentLine.setQuantity(5, false);
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(2));
        transactions = request.transaction.transactionLines;
        expect(transactions).toHaveLength(1);
        expectGeneralProperties(request, { order: order, ticketMedium: "NONE" });
        expect(transactions[0].mainProduct.quantity).toBe(4); // delta
        expect(transactions[0].subProducts[0].quantity).toBe(8); // starter: (10/5)*4
        expect(transactions[0].subProducts[1].quantity).toBe(12); // wine: (15/5)*4
        expect(transactions[0].subProducts[2].quantity).toBe(4); // burger: (5/5)*4
        expect(transactions[0].lineTotal).toBe(232);

        // If we sign again without changes, no new request
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(2));

        // Decrease parent qty 5→3: delta=-2, correction
        // After setQuantity(3): parent=3, starter=6, wine=9, burger=3.
        // subQty: starter=(6/3)*2=4, wine=(9/3)*2=6, burger=(3/3)*2=2 → negated. lineTotal=-116
        parentLine.setQuantity(3, false);
        await store.blackbox.signOrder.sign(order, "1234567890", true);
        await waitForUnawaitedCalls(() => expect(signOrderCalledTimes).toBe(3));
        transactions = request.transaction.transactionLines;
        expect(transactions).toHaveLength(1);
        expectGeneralProperties(request, { order: order, ticketMedium: "NONE" });
        expect(transactions[0].mainProduct.quantity).toBe(-2);
        expect(transactions[0].mainProduct.negQuantityReason).toBe("CORRECTION");
        expect(transactions[0].subProducts[0].quantity).toBe(-4); // starter: (6/3)*2, negated
        expect(transactions[0].subProducts[0].negQuantityReason).toBe("CORRECTION");
        expect(transactions[0].subProducts[1].quantity).toBe(-6); // wine: (9/3)*2, negated
        expect(transactions[0].subProducts[1].negQuantityReason).toBe("CORRECTION");
        expect(transactions[0].subProducts[2].quantity).toBe(-2); // burger: (3/3)*2, negated
        expect(transactions[0].subProducts[2].negQuantityReason).toBe("CORRECTION");
    });
    //FIXME: handle combo correction (when editing combo config (long press combo line))
});
