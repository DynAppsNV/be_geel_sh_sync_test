import { test, expect, describe } from "@odoo/hoot";
import {
    expectTransactionLine,
    generatePosOrder,
    setupPosBlackboxEnv,
    waitForDelayedCalls,
    expectGeneralProperties,
    expectCostCenter,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { SplitBillScreen } from "@pos_restaurant/app/screens/split_bill_screen/split_bill_screen";

definePosModels();

// see 'enterprise/l10n_be_pos_blackbox/static/tests/unit/data/json/m122_sign_cost_center_change.json' for an example request
describe("sign_cost_center_change", () => {
    test("data generation", async () => {
        const { promise, resolver } = waitForDelayedCalls();
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M122_signCostCenterChange") {
                resolver(body.variables.data);
            }
        });
        const models = store.models;
        const table1 = models["restaurant.table"].find((t) => t.table_number === 1);
        const table2 = models["restaurant.table"].find((t) => t.table_number === 2);
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const burger = models["product.product"].find((p) => p.name === "Burger of the Chef");
        const order = generatePosOrder(models, [
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
            },
        ]);
        order.table_id = table1;
        const oldCostCenter = order.generateCostCenterInput();
        order.table_id = table2;
        const newCostCenter = order.generateCostCenterInput();
        await store.blackbox.signCostCenterChange.signCostCenterChange(
            order,
            oldCostCenter,
            newCostCenter,
            "1234567890"
        );
        const input = await promise;
        const financials = input.financials;

        // Check general properties
        expectGeneralProperties(input, { order: order, ticketMedium: "NONE" });
        expect(input.transfer.from.transaction.transactionTotal).toBe(-40);
        expect(input.transfer.to.transaction.transactionTotal).toBe(40);

        const toTrc = input.transfer.to.transaction.transactionLines;
        const fromTrc = input.transfer.from.transaction.transactionLines;
        const toCenter = input.transfer.to.costCenter;
        const fromCenter = input.transfer.from.costCenter;

        // Check transaction details - Dry Martini
        expectTransactionLine(
            fromTrc[0],
            martini,
            -1,
            "PIECE",
            12,
            "A",
            "SINGLE_PRODUCT",
            "COST_CENTER_CHANGE"
        );

        // Check transaction details - Burger of the Chef
        expectTransactionLine(
            fromTrc[1],
            burger,
            -1,
            "PIECE",
            28,
            "B",
            "SINGLE_PRODUCT",
            "COST_CENTER_CHANGE"
        );

        // Check transaction details - Dry Martini
        expectTransactionLine(toTrc[0], martini, 1, "PIECE", 12, "A", "SINGLE_PRODUCT");

        // Check transaction details - Burger of the Chef
        expectTransactionLine(toTrc[1], burger, 1, "PIECE", 28, "B", "SINGLE_PRODUCT");

        // Check cost center details
        expect(fromCenter).toEqual(oldCostCenter);
        expect(toCenter).toEqual(newCostCenter);

        // Check payment details
        expect(financials).toBeEmpty();
    });

    async function setupBlackboxCostCenterEnv() {
        const { promise, resolver } = waitForDelayedCalls();
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M122_signCostCenterChange") {
                resolver(body.variables.data);
            }
        });
        const table1 = store.models["restaurant.table"].find((t) => t.table_number === 1);
        const table2 = store.models["restaurant.table"].find((t) => t.table_number === 2);
        return { store, table1, table2, promise };
    }

    function expectCostCenterTransfer(request, fromTableNum, toTableNum, fromRef, toRef) {
        expect(request).not.toBeEmpty();
        expectCostCenter(
            request.transfer.from.costCenter,
            fromTableNum.toString(),
            "TABLE",
            fromRef
        );
        expectCostCenter(request.transfer.to.costCenter, toTableNum.toString(), "TABLE", toRef);
    }

    test("called at right time (when transferring order to an empty table)", async () => {
        const { store, table1, table2, promise } = await setupBlackboxCostCenterEnv();
        const order = await getFilledOrder(store);
        order.table_id = table1;
        expect(order.table_id.table_number).toBe(1);
        await store.syncAllOrders();
        await store.transferOrder(order.uuid, table2);
        const request = await promise;
        expect(order.lines.length).toBe(2);
        expect(order.table_id.table_number).toBe(2);
        expectCostCenterTransfer(request, 1, 2, order.uuid, order.uuid);
    });

    test("called at right time (when transferring order to a table with existing order)", async () => {
        const { store, table1, table2, promise } = await setupBlackboxCostCenterEnv();
        const orderA = await getFilledOrder(store);
        orderA.table_id = table1;
        expect(orderA.table_id.table_number).toBe(1);
        const orderB = await getFilledOrder(store);
        orderB.table_id = table2;
        expect(orderB.table_id.table_number).toBe(2);
        expect(orderB.lines[0].qty).toBe(3);
        await store.syncAllOrders();
        await store.transferOrder(orderA.uuid, table2);
        const request = await promise;
        expect(orderA.isEmpty()).toBe(true);
        expect(orderB.lines[0].qty).toBe(6);
        expectCostCenterTransfer(request, 1, 2, orderA.uuid, orderB.uuid);
    });

    test("called at right time (merge orders)", async () => {
        const { store, table1, table2, promise } = await setupBlackboxCostCenterEnv();
        const order = await getFilledOrder(store);
        order.table_id = table1;
        expect(order.table_id.table_number).toBe(1);
        await store.syncAllOrders();
        await store.mergeTableOrders(order.uuid, table2);
        const request = await promise;
        expect(order.lines.length).toBe(2);
        expect(order.table_id.table_number).toBe(2);
        expectCostCenterTransfer(request, 1, 2, order.uuid, order.uuid);
    });

    test("called at right time (when merging order to a table with existing order) then unmergeTable ", async () => {
        let request = null;
        let costCenterChangeCount = 0;
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M122_signCostCenterChange") {
                request = body.variables.data;
                costCenterChangeCount++;
            }
        });
        const table1 = store.models["restaurant.table"].find((t) => t.table_number === 1);
        const table2 = store.models["restaurant.table"].find((t) => t.table_number === 2);

        const orderA = await getFilledOrder(store);
        expect(orderA.priceIncl).toBe(185);
        orderA.table_id = table1;
        expect(orderA.table_id.table_number).toBe(1);
        const orderB = await getFilledOrder(store);
        expect(orderB.priceIncl).toBe(185);
        orderB.table_id = table2;
        expect(orderB.table_id.table_number).toBe(2);
        expect(orderB.lines[0].qty).toBe(3);
        await store.mergeTableOrders(orderA.uuid, table2);
        expect(costCenterChangeCount).toBe(1);
        expect(orderA.isEmpty()).toBe(true);
        expect(orderA.priceIncl).toBe(0);
        expect(orderB.lines[0].qty).toBe(6);
        expect(orderB.priceIncl).toBe(370);
        expectCostCenterTransfer(request, 1, 2, orderA.uuid, orderB.uuid);
        // Now unmerge the table A from B
        const newOrderA = await store.restoreOrdersToOriginalTable(orderB, table1);
        expect(newOrderA.priceIncl).toBe(185);
        expect(costCenterChangeCount).toBe(2);
        expect(newOrderA.lines.length).toBe(2);
        expect(newOrderA.table_id.table_number).toBe(1);
        expect(orderB.lines.length).toBe(2);
        expect(orderB.lines[0].qty).toBe(3);
        expect(orderB.priceIncl).toBe(185);
        expectCostCenterTransfer(request, 2, 1, orderB.uuid, newOrderA.uuid);
    });

    test("Transfer order A (without GD) to order B (with 10% GD)", async () => {
        let costCenterChangeRequest = null;
        let costCenterChangeCount = 0;
        let signOrderCount = 0;
        let signOrderRequest = null;
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M122_signCostCenterChange") {
                costCenterChangeRequest = body.variables.data;
                costCenterChangeCount++;
            } else if (body.operationName === "M121_signOrder") {
                signOrderRequest = body.variables.data;
                signOrderCount++;
            }
        });
        // Setup orders
        const table1 = store.models["restaurant.table"].find((t) => t.table_number === 1);
        const table2 = store.models["restaurant.table"].find((t) => t.table_number === 2);
        const orderA = await getFilledOrder(store);
        // Add combo to order A:
        const comp = await mountWithCleanup(ProductScreen, { props: { orderUuid: orderA.uuid } });
        await comp.addProductToOrder(store.models["product.template"].get(17));
        // Set price change to order A lines
        orderA.lines[0].price_type = "manual";
        orderA.lines[0].setUnitPrice(10); // set a price change
        store.setDiscountFromUI(orderA.lines[1], 15); // set a discount on the line

        orderA.table_id = table1;
        expect(orderA.table_id.table_number).toBe(1);
        const orderB = await getFilledOrder(store);
        orderB.table_id = table2;
        await store.applyDiscount(10, orderB); // apply global discount of 10%
        expect(orderB.table_id.table_number).toBe(2);
        expect(orderB.lines[0].qty).toBe(3);
        expect(costCenterChangeCount).toBe(0);
        expect(signOrderCount).toBe(0);
        orderA.updateLastTransactionLines();
        orderB.updateLastTransactionLines();

        // Transfer A to B:
        // - This should trigger a cost center change (to transfer the lines from table 1 to table 2)
        // - This should trigger a sign order to correct the global discount of lines from order A:
        //   - Negate the original transaction lines of order A
        //   - Add new transaction lines for order A with the correct global discount (10%)
        await store.transferOrder(orderA.uuid, table2);
        expect(costCenterChangeCount).toBe(1);
        expect(signOrderCount).toBe(1);

        expect(orderA.isEmpty()).toBe(true);
        expect(orderB.lines[0].qty).toBe(3);
        expect(orderB.lines.length).toBe(10);
        expectCostCenterTransfer(costCenterChangeRequest, 1, 2, orderA.uuid, orderB.uuid);
        const expectFromTransaction = {
            transactionLines: [
                {
                    lineType: "SINGLE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_5",
                        productName: "Bourgogne Red",
                        departmentId: "6",
                        departmentName: "Wines",
                        quantity: -3,
                        quantityType: "PIECE",
                        unitPrice: 35,
                        vats: [
                            {
                                label: "A",
                                price: -105,
                                priceChanges: [
                                    {
                                        id: "3",
                                        groupingId: 1,
                                        name: "UNIT_PRICE_CHANGE",
                                        scope: "LINE",
                                        type: "PUBLIC",
                                        amount: 75,
                                    },
                                ],
                            },
                        ],
                        negQuantityReason: "COST_CENTER_CHANGE",
                    },
                    lineTotal: -30,
                },
                {
                    lineType: "SINGLE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_6",
                        productName: "Chardonnay White",
                        departmentId: "6",
                        departmentName: "Wines",
                        quantity: -2,
                        quantityType: "PIECE",
                        unitPrice: 40,
                        vats: [
                            {
                                label: "A",
                                price: -80,
                                priceChanges: [
                                    {
                                        id: "4_15P",
                                        groupingId: 2,
                                        name: "DISCOUNT_15P",
                                        scope: "LINE",
                                        type: "PUBLIC",
                                        amount: 12,
                                    },
                                ],
                            },
                        ],
                        negQuantityReason: "COST_CENTER_CHANGE",
                    },
                    lineTotal: -68,
                },
                {
                    lineType: "COMPOSITE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_17",
                        productName: "Business Menu All-In",
                        departmentId: "11",
                        departmentName: "Menu",
                        quantity: -1,
                        quantityType: "PIECE",
                        unitPrice: 58,
                        vats: [],
                        negQuantityReason: "COST_CENTER_CHANGE",
                    },
                    lineTotal: -58,
                    subProducts: [
                        {
                            productId: "product_id_9",
                            productName: "Carpaccio Beef",
                            departmentId: "7",
                            departmentName: "Starters",
                            quantity: -1,
                            quantityType: "PIECE",
                            unitPrice: 20,
                            vats: [
                                {
                                    label: "B",
                                    price: -20,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 3,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 3.89,
                                        },
                                    ],
                                },
                            ],
                            negQuantityReason: "COST_CENTER_CHANGE",
                        },
                        {
                            productId: "product_id_10",
                            productName: "Burger of the Chef",
                            departmentId: "9",
                            departmentName: "Main Dishes",
                            quantity: -1,
                            quantityType: "PIECE",
                            unitPrice: 28,
                            vats: [
                                {
                                    label: "B",
                                    price: -28,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 3,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 5.44,
                                        },
                                    ],
                                },
                            ],
                            negQuantityReason: "COST_CENTER_CHANGE",
                        },
                        {
                            productId: "product_id_8",
                            productName: "Matching Wines",
                            departmentId: "6",
                            departmentName: "Wines",
                            quantity: -1,
                            quantityType: "PIECE",
                            unitPrice: 24,
                            vats: [
                                {
                                    label: "A",
                                    price: -24,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 3,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 4.67,
                                        },
                                    ],
                                },
                            ],
                            negQuantityReason: "COST_CENTER_CHANGE",
                        },
                    ],
                },
            ],
            transactionTotal: -156,
        };
        expect(costCenterChangeRequest.transfer.from.transaction).toEqual(expectFromTransaction);
        const expectSignOrder = {
            transactionLines: [
                {
                    lineType: "SINGLE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_5",
                        productName: "Bourgogne Red",
                        departmentId: "6",
                        departmentName: "Wines",
                        quantity: -3,
                        quantityType: "PIECE",
                        unitPrice: 35,
                        vats: [
                            {
                                label: "A",
                                price: -105,
                                priceChanges: [
                                    {
                                        id: "3",
                                        groupingId: 1,
                                        name: "UNIT_PRICE_CHANGE",
                                        scope: "LINE",
                                        type: "PUBLIC",
                                        amount: 75,
                                    },
                                ],
                            },
                        ],
                        negQuantityReason: "PRICE_CHANGE",
                    },
                    lineTotal: -30,
                },
                {
                    lineType: "SINGLE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_5",
                        productName: "Bourgogne Red",
                        departmentId: "6",
                        departmentName: "Wines",
                        quantity: 3,
                        quantityType: "PIECE",
                        unitPrice: 35,
                        vats: [
                            {
                                label: "A",
                                price: 105,
                                priceChanges: [
                                    {
                                        id: "2_10P",
                                        groupingId: 1,
                                        name: "GLOBAL_DISCOUNT_10P",
                                        scope: "EVENT",
                                        type: "PUBLIC",
                                        amount: -3,
                                    },
                                    {
                                        id: "3",
                                        groupingId: 1,
                                        name: "UNIT_PRICE_CHANGE",
                                        scope: "LINE",
                                        type: "PUBLIC",
                                        amount: -75,
                                    },
                                ],
                            },
                        ],
                    },
                    lineTotal: 27,
                },
                {
                    lineType: "SINGLE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_6",
                        productName: "Chardonnay White",
                        departmentId: "6",
                        departmentName: "Wines",
                        quantity: -2,
                        quantityType: "PIECE",
                        unitPrice: 40,
                        vats: [
                            {
                                label: "A",
                                price: -80,
                                priceChanges: [
                                    {
                                        id: "4_15P",
                                        groupingId: 2,
                                        name: "DISCOUNT_15P",
                                        scope: "LINE",
                                        type: "PUBLIC",
                                        amount: 12,
                                    },
                                ],
                            },
                        ],
                        negQuantityReason: "PRICE_CHANGE",
                    },
                    lineTotal: -68,
                },
                {
                    lineType: "SINGLE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_6",
                        productName: "Chardonnay White",
                        departmentId: "6",
                        departmentName: "Wines",
                        quantity: 2,
                        quantityType: "PIECE",
                        unitPrice: 40,
                        vats: [
                            {
                                label: "A",
                                price: 80,
                                priceChanges: [
                                    {
                                        id: "2_10P",
                                        groupingId: 1,
                                        name: "GLOBAL_DISCOUNT_10P",
                                        scope: "EVENT",
                                        type: "PUBLIC",
                                        amount: -6.8,
                                    },
                                    {
                                        id: "4_15P",
                                        groupingId: 2,
                                        name: "DISCOUNT_15P",
                                        scope: "LINE",
                                        type: "PUBLIC",
                                        amount: -12,
                                    },
                                ],
                            },
                        ],
                    },
                    lineTotal: 61.2,
                },
                {
                    lineType: "COMPOSITE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_17",
                        productName: "Business Menu All-In",
                        departmentId: "11",
                        departmentName: "Menu",
                        quantity: -1,
                        quantityType: "PIECE",
                        unitPrice: 58,
                        vats: [],
                        negQuantityReason: "PRICE_CHANGE",
                    },
                    lineTotal: -58,
                    subProducts: [
                        {
                            productId: "product_id_9",
                            productName: "Carpaccio Beef",
                            departmentId: "7",
                            departmentName: "Starters",
                            quantity: -1,
                            quantityType: "PIECE",
                            unitPrice: 20,
                            vats: [
                                {
                                    label: "B",
                                    price: -20,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 3,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 3.89,
                                        },
                                    ],
                                },
                            ],
                            negQuantityReason: "PRICE_CHANGE",
                        },
                        {
                            productId: "product_id_10",
                            productName: "Burger of the Chef",
                            departmentId: "9",
                            departmentName: "Main Dishes",
                            quantity: -1,
                            quantityType: "PIECE",
                            unitPrice: 28,
                            vats: [
                                {
                                    label: "B",
                                    price: -28,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 3,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 5.44,
                                        },
                                    ],
                                },
                            ],
                            negQuantityReason: "PRICE_CHANGE",
                        },
                        {
                            productId: "product_id_8",
                            productName: "Matching Wines",
                            departmentId: "6",
                            departmentName: "Wines",
                            quantity: -1,
                            quantityType: "PIECE",
                            unitPrice: 24,
                            vats: [
                                {
                                    label: "A",
                                    price: -24,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 3,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 4.67,
                                        },
                                    ],
                                },
                            ],
                            negQuantityReason: "PRICE_CHANGE",
                        },
                    ],
                },
                {
                    lineType: "COMPOSITE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_17",
                        productName: "Business Menu All-In",
                        departmentId: "11",
                        departmentName: "Menu",
                        quantity: 1,
                        quantityType: "PIECE",
                        unitPrice: 58,
                        vats: [],
                    },
                    lineTotal: 52.2,
                    subProducts: [
                        {
                            productId: "product_id_9",
                            productName: "Carpaccio Beef",
                            departmentId: "7",
                            departmentName: "Starters",
                            quantity: 1,
                            quantityType: "PIECE",
                            unitPrice: 20,
                            vats: [
                                {
                                    label: "B",
                                    price: 20,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 3,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -3.89,
                                        },
                                        {
                                            id: "2_10P",
                                            groupingId: 1,
                                            name: "GLOBAL_DISCOUNT_10P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: -1.61,
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            productId: "product_id_10",
                            productName: "Burger of the Chef",
                            departmentId: "9",
                            departmentName: "Main Dishes",
                            quantity: 1,
                            quantityType: "PIECE",
                            unitPrice: 28,
                            vats: [
                                {
                                    label: "B",
                                    price: 28,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 3,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -5.44,
                                        },
                                        {
                                            id: "2_10P",
                                            groupingId: 1,
                                            name: "GLOBAL_DISCOUNT_10P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: -2.26,
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            productId: "product_id_8",
                            productName: "Matching Wines",
                            departmentId: "6",
                            departmentName: "Wines",
                            quantity: 1,
                            quantityType: "PIECE",
                            unitPrice: 24,
                            vats: [
                                {
                                    label: "A",
                                    price: 24,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 3,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -4.67,
                                        },
                                        {
                                            id: "2_10P",
                                            groupingId: 1,
                                            name: "GLOBAL_DISCOUNT_10P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: -1.93,
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
            transactionTotal: -15.6,
        };
        expect(signOrderRequest.transaction).toEqual(expectSignOrder);
    });

    test("Transfer order A (with 10% GD) to order B (without GD)", async () => {
        let costCenterChangeRequest = null;
        let costCenterChangeCount = 0;
        let signOrderCount = 0;
        let signOrderRequest = null;
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M122_signCostCenterChange") {
                costCenterChangeRequest = body.variables.data;
                costCenterChangeCount++;
            } else if (body.operationName === "M121_signOrder") {
                signOrderRequest = body.variables.data;
                signOrderCount++;
            }
        });
        // Setup orders
        const table1 = store.models["restaurant.table"].find((t) => t.table_number === 1);
        const table2 = store.models["restaurant.table"].find((t) => t.table_number === 2);
        const orderA = await getFilledOrder(store);
        // Add combo to order A:
        const comp = await mountWithCleanup(ProductScreen, { props: { orderUuid: orderA.uuid } });
        await comp.addProductToOrder(store.models["product.template"].get(17));
        // Set price change to order A lines
        orderA.lines[0].price_type = "manual";
        orderA.lines[0].setUnitPrice(10); // set a price change
        store.setDiscountFromUI(orderA.lines[1], 15); // set a discount on the line
        orderA.table_id = table1;
        expect(orderA.table_id.table_number).toBe(1);
        const orderB = await getFilledOrder(store);
        orderB.table_id = table2;
        await store.applyDiscount(10, orderA); // apply global discount of 10%
        expect(orderB.table_id.table_number).toBe(2);
        expect(orderB.lines[0].qty).toBe(3);
        expect(costCenterChangeCount).toBe(0);
        expect(signOrderCount).toBe(0);
        orderA.updateLastTransactionLines();
        orderB.updateLastTransactionLines();

        // Transfer A to B:
        // - This should trigger a cost center change (to transfer the lines from table 1 to table 2)
        // - This should trigger a sign order to correct the global discount of lines from order B (since the GD is also transferred and applied to B lines):
        //   - Negate the original transaction lines of order B
        //   - Add new transaction lines for order B with the correct global discount (10%)
        await store.transferOrder(orderA.uuid, table2);
        expect(costCenterChangeCount).toBe(1);
        expect(signOrderCount).toBe(1);

        expect(orderA.isEmpty()).toBe(true);
        expect(orderB.lines[0].qty).toBe(3);
        expect(orderB.lines.length).toBe(10);

        expectCostCenterTransfer(costCenterChangeRequest, 1, 2, orderA.uuid, orderB.uuid);
        const expectFromTransaction = {
            transactionLines: [
                {
                    lineType: "SINGLE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_5",
                        productName: "Bourgogne Red",
                        departmentId: "6",
                        departmentName: "Wines",
                        quantity: -3,
                        quantityType: "PIECE",
                        unitPrice: 35,
                        vats: [
                            {
                                label: "A",
                                price: -105,
                                priceChanges: [
                                    {
                                        id: "2_10P",
                                        groupingId: 2,
                                        name: "GLOBAL_DISCOUNT_10P",
                                        scope: "EVENT",
                                        type: "PUBLIC",
                                        amount: 3,
                                    },
                                    {
                                        id: "3",
                                        groupingId: 1,
                                        name: "UNIT_PRICE_CHANGE",
                                        scope: "LINE",
                                        type: "PUBLIC",
                                        amount: 75,
                                    },
                                ],
                            },
                        ],
                        negQuantityReason: "COST_CENTER_CHANGE",
                    },
                    lineTotal: -27,
                },
                {
                    lineType: "SINGLE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_6",
                        productName: "Chardonnay White",
                        departmentId: "6",
                        departmentName: "Wines",
                        quantity: -2,
                        quantityType: "PIECE",
                        unitPrice: 40,
                        vats: [
                            {
                                label: "A",
                                price: -80,
                                priceChanges: [
                                    {
                                        id: "2_10P",
                                        groupingId: 2,
                                        name: "GLOBAL_DISCOUNT_10P",
                                        scope: "EVENT",
                                        type: "PUBLIC",
                                        amount: 6.8,
                                    },
                                    {
                                        id: "4_15P",
                                        groupingId: 3,
                                        name: "DISCOUNT_15P",
                                        scope: "LINE",
                                        type: "PUBLIC",
                                        amount: 12,
                                    },
                                ],
                            },
                        ],
                        negQuantityReason: "COST_CENTER_CHANGE",
                    },
                    lineTotal: -61.2,
                },
                {
                    lineType: "COMPOSITE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_17",
                        productName: "Business Menu All-In",
                        departmentId: "11",
                        departmentName: "Menu",
                        quantity: -1,
                        quantityType: "PIECE",
                        unitPrice: 58,
                        vats: [],
                        negQuantityReason: "COST_CENTER_CHANGE",
                    },
                    lineTotal: -52.2,
                    subProducts: [
                        {
                            productId: "product_id_9",
                            productName: "Carpaccio Beef",
                            departmentId: "7",
                            departmentName: "Starters",
                            quantity: -1,
                            quantityType: "PIECE",
                            unitPrice: 20,
                            vats: [
                                {
                                    label: "B",
                                    price: -20,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 4,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 3.89,
                                        },
                                        {
                                            id: "2_10P",
                                            groupingId: 2,
                                            name: "GLOBAL_DISCOUNT_10P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: 1.61,
                                        },
                                    ],
                                },
                            ],
                            negQuantityReason: "COST_CENTER_CHANGE",
                        },
                        {
                            productId: "product_id_10",
                            productName: "Burger of the Chef",
                            departmentId: "9",
                            departmentName: "Main Dishes",
                            quantity: -1,
                            quantityType: "PIECE",
                            unitPrice: 28,
                            vats: [
                                {
                                    label: "B",
                                    price: -28,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 4,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 5.44,
                                        },
                                        {
                                            id: "2_10P",
                                            groupingId: 2,
                                            name: "GLOBAL_DISCOUNT_10P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: 2.26,
                                        },
                                    ],
                                },
                            ],
                            negQuantityReason: "COST_CENTER_CHANGE",
                        },
                        {
                            productId: "product_id_8",
                            productName: "Matching Wines",
                            departmentId: "6",
                            departmentName: "Wines",
                            quantity: -1,
                            quantityType: "PIECE",
                            unitPrice: 24,
                            vats: [
                                {
                                    label: "A",
                                    price: -24,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 4,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 4.67,
                                        },
                                        {
                                            id: "2_10P",
                                            groupingId: 2,
                                            name: "GLOBAL_DISCOUNT_10P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: 1.93,
                                        },
                                    ],
                                },
                            ],
                            negQuantityReason: "COST_CENTER_CHANGE",
                        },
                    ],
                },
            ],
            transactionTotal: -140.4,
        };
        expect(costCenterChangeRequest.transfer.from.transaction).toEqual(expectFromTransaction);

        const expectSignOrder = {
            transactionLines: [
                {
                    lineType: "SINGLE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_5",
                        productName: "Bourgogne Red",
                        departmentId: "6",
                        departmentName: "Wines",
                        quantity: -3,
                        quantityType: "PIECE",
                        unitPrice: 35,
                        vats: [{ label: "A", price: -105, priceChanges: [] }],
                        negQuantityReason: "PRICE_CHANGE",
                    },
                    lineTotal: -105,
                },
                {
                    lineType: "SINGLE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_5",
                        productName: "Bourgogne Red",
                        departmentId: "6",
                        departmentName: "Wines",
                        quantity: 3,
                        quantityType: "PIECE",
                        unitPrice: 35,
                        vats: [
                            {
                                label: "A",
                                price: 105,
                                priceChanges: [
                                    {
                                        id: "2_10P",
                                        groupingId: 5,
                                        name: "GLOBAL_DISCOUNT_10P",
                                        scope: "EVENT",
                                        type: "PUBLIC",
                                        amount: -10.5,
                                    },
                                ],
                            },
                        ],
                    },
                    lineTotal: 94.5,
                },
                {
                    lineType: "SINGLE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_6",
                        productName: "Chardonnay White",
                        departmentId: "6",
                        departmentName: "Wines",
                        quantity: -2,
                        quantityType: "PIECE",
                        unitPrice: 40,
                        vats: [{ label: "A", price: -80, priceChanges: [] }],
                        negQuantityReason: "PRICE_CHANGE",
                    },
                    lineTotal: -80,
                },
                {
                    lineType: "SINGLE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_6",
                        productName: "Chardonnay White",
                        departmentId: "6",
                        departmentName: "Wines",
                        quantity: 2,
                        quantityType: "PIECE",
                        unitPrice: 40,
                        vats: [
                            {
                                label: "A",
                                price: 80,
                                priceChanges: [
                                    {
                                        id: "2_10P",
                                        groupingId: 5,
                                        name: "GLOBAL_DISCOUNT_10P",
                                        scope: "EVENT",
                                        type: "PUBLIC",
                                        amount: -8,
                                    },
                                ],
                            },
                        ],
                    },
                    lineTotal: 72,
                },
            ],
            transactionTotal: -18.5,
        };
        expect(signOrderRequest.transaction).toEqual(expectSignOrder);
    });

    test("called at right time (when splitting an order with GD via transfer)", async () => {
        let signOrderCount = 0;
        let signOrderRequest = null;
        let costCenterChangeCount = 0;
        let costCenterChangeRequest = null;
        const store = await setupPosBlackboxEnv(async (mockRequest) => {
            const body = await mockRequest.json();
            if (body.operationName === "M121_signOrder") {
                signOrderRequest = body.variables.data;
                signOrderCount++;
            } else if (body.operationName === "M122_signCostCenterChange") {
                costCenterChangeRequest = body.variables.data;
                costCenterChangeCount++;
            }
        });

        const table1 = store.models["restaurant.table"].find((t) => t.table_number === 1);
        const order = await getFilledOrder(store);
        order.table_id = table1;

        // Apply 10% global discount and simulate the order having been previously signed
        await store.applyDiscount(10, order);
        expect(order.globalDiscountPc).toBe(10);
        order.updateLastTransactionLines();

        expect(signOrderCount).toBe(0);
        expect(costCenterChangeCount).toBe(0);

        // Prevent the startTransferOrder UI navigation from running in the test environment
        patchWithCleanup(store, { startTransferOrder() {} });

        // Mount SplitBillScreen and select all 3 units of the first line (Bourgogne Red)
        // to transfer to a new split order. The second line (Chardonnay White, qty=2)
        // stays on the original order, so totOrderQty=5 != selectedQty=3 → split happens.
        const comp = await mountWithCleanup(SplitBillScreen, {
            props: { orderUuid: order.uuid },
        });
        const bourgogneLine = order.lines[0]; // product_5 (Bourgogne Red), qty=3
        const bourgogneProduct = bourgogneLine.product_id; // capture before transfer (line is moved after)
        comp.onClickLine(bourgogneLine);
        comp.onClickLine(bourgogneLine);
        comp.onClickLine(bourgogneLine);
        // qtyTracker[bourgogneLine.uuid] = 3 (full qty selected)

        await comp.transferSplittedOrder({ stopPropagation: () => {} });

        // Since the original order had a GD (10%) and transferSplittedOrder does NOT pass the
        // GD to the new split order, a signOrder correction must be sent first, followed by
        // the signCostCenterChange to record the lines moving to the new split order.
        expect(signOrderCount).toBe(1);
        expect(costCenterChangeCount).toBe(1);

        // Verify the signOrder correction structure:
        // Two entries for Bourgogne Red (qty=3):
        //   - NEG: with 10% GD applied, reason PRICE_CHANGE
        //   - POS: without GD (targetGlobalDiscount = 0)
        const transLines = signOrderRequest.transaction.transactionLines;
        expect(transLines.length).toBe(2);

        const negLine = transLines[0];
        const posLine = transLines[1];

        // NEG line: Bourgogne Red negated with GD=10%, reason=PRICE_CHANGE
        // unitPrice=35, vats[0].price = 35 * (-3) = -105 (base, before GD priceChange)
        expectTransactionLine(
            negLine,
            bourgogneProduct,
            -3,
            "PIECE",
            35,
            "A",
            "SINGLE_PRODUCT",
            "PRICE_CHANGE"
        );

        // POS line: Bourgogne Red added back without GD (globalDiscount=0)
        // unitPrice=35, vats[0].price = 35 * 3 = 105 (no GD priceChange)
        expectTransactionLine(posLine, bourgogneProduct, 3, "PIECE", 35, "A", "SINGLE_PRODUCT");

        // The cost center change should transfer from table 1 to the new split order
        expect(costCenterChangeRequest.transfer.from.costCenter.id).toBe("1");
        expect(costCenterChangeRequest.transfer.from.costCenter.type).toBe("TABLE");
    });
});
