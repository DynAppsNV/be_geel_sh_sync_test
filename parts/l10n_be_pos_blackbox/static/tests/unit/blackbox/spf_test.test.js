import { test, describe, expect } from "@odoo/hoot";
import {
    setupPosBlackboxEnv,
    expectTransactionTotals,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

definePosModels();

const getBlackboxOrderSign = (order) => {
    const generator = new InputGenerator({
        models: order.models,
        order: order,
        inszOrBisNumber: "971234567890",
    });
    const data = generator.generateSignOrderInput();
    data.bookingPeriodId = "0ca2ebb7-5f77-4d03-99a9-77b5673ab248"; // Set a fixed bookingPeriodId for testing
    data.posDateTime = "2019-03-11T10:30:05.620+01:00"; // Set a fixed posDateTime for testing
    data.deviceId = "ced7e687-d7c0-4431-b2c0-d13c14d227ec"; // Set a fixed deviceId for testing
    data.costCenter.reference = "8db2ff9e-7d17-4b9f-9105-0d65abdc48e2"; // Set a fixed cost center reference for testing
    data.posFiscalTicketNo = 1;
    order.updateLastTransactionLines();
    return data;
};

describe("SPF Test", () => {
    test("Business Menu All-In generation", async () => {
        const store = await setupPosBlackboxEnv();
        store.addNewOrder();
        const order = store.getOrder();
        const comp = await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });
        await comp.addProductToOrder(store.models["product.template"].get(17));

        const firstInputData = {
            transactionLines: [
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
                    lineTotal: 58,
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -3.89,
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -5.44,
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -4.67,
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
            transactionTotal: 58,
        };
        // Add 1 Business Menu All-In to the order
        const firstInput = getBlackboxOrderSign(order);
        expectTransactionTotals(firstInput.transaction, order.currency);
        expect(firstInput.transaction).toEqual(firstInputData);

        // Update quantity of Business Menu All-In to 5
        order.lines[0].setQuantity(5, true);

        const secondInputData = {
            transactionLines: [
                {
                    lineType: "COMPOSITE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_17",
                        productName: "Business Menu All-In",
                        departmentId: "11",
                        departmentName: "Menu",
                        quantity: 4,
                        quantityType: "PIECE",
                        unitPrice: 58,
                        vats: [],
                    },
                    lineTotal: 232,
                    subProducts: [
                        {
                            productId: "product_id_9",
                            productName: "Carpaccio Beef",
                            departmentId: "7",
                            departmentName: "Starters",
                            quantity: 4,
                            quantityType: "PIECE",
                            unitPrice: 20,
                            vats: [
                                {
                                    label: "B",
                                    price: 80,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -15.56,
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
                            quantity: 4,
                            quantityType: "PIECE",
                            unitPrice: 28,
                            vats: [
                                {
                                    label: "B",
                                    price: 112,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -21.76,
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
                            quantity: 4,
                            quantityType: "PIECE",
                            unitPrice: 24,
                            vats: [
                                {
                                    label: "A",
                                    price: 96,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -18.68,
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
            transactionTotal: 232,
        };
        // Add 4 Business Menu All-In to the order (total 5)
        const secondInput = getBlackboxOrderSign(order);
        expectTransactionTotals(secondInput.transaction, order.currency);
        expect(secondInput.transaction).toEqual(secondInputData);

        // Add a discount of 10% on the Business Menu All-In
        await store.setDiscountFromUI(order.lines[0], 10);

        const thirdInputData = {
            transactionLines: [
                {
                    lineType: "COMPOSITE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_17",
                        productName: "Business Menu All-In",
                        departmentId: "11",
                        departmentName: "Menu",
                        quantity: -5,
                        quantityType: "PIECE",
                        unitPrice: 58,
                        vats: [],
                        negQuantityReason: "PRICE_CHANGE",
                    },
                    lineTotal: -290,
                    subProducts: [
                        {
                            productId: "product_id_9",
                            productName: "Carpaccio Beef",
                            departmentId: "7",
                            departmentName: "Starters",
                            quantity: -5,
                            quantityType: "PIECE",
                            unitPrice: 20,
                            vats: [
                                {
                                    label: "B",
                                    price: -100,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 19.45,
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
                            quantity: -5,
                            quantityType: "PIECE",
                            unitPrice: 28,
                            vats: [
                                {
                                    label: "B",
                                    price: -140,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 27.2,
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
                            quantity: -5,
                            quantityType: "PIECE",
                            unitPrice: 24,
                            vats: [
                                {
                                    label: "A",
                                    price: -120,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 23.35,
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
                        quantity: 5,
                        quantityType: "PIECE",
                        unitPrice: 58,
                        vats: [],
                    },
                    lineTotal: 261,
                    subProducts: [
                        {
                            productId: "product_id_9",
                            productName: "Carpaccio Beef",
                            departmentId: "7",
                            departmentName: "Starters",
                            quantity: 5,
                            quantityType: "PIECE",
                            unitPrice: 20,
                            vats: [
                                {
                                    label: "B",
                                    price: 100,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -19.45,
                                        },
                                        {
                                            id: "4_10P",
                                            groupingId: 2,
                                            name: "DISCOUNT_10P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: -8.06,
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
                            quantity: 5,
                            quantityType: "PIECE",
                            unitPrice: 28,
                            vats: [
                                {
                                    label: "B",
                                    price: 140,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -27.2,
                                        },
                                        {
                                            id: "4_10P",
                                            groupingId: 2,
                                            name: "DISCOUNT_10P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: -11.28,
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
                            quantity: 5,
                            quantityType: "PIECE",
                            unitPrice: 24,
                            vats: [
                                {
                                    label: "A",
                                    price: 120,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -23.35,
                                        },
                                        {
                                            id: "4_10P",
                                            groupingId: 2,
                                            name: "DISCOUNT_10P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: -9.67,
                                        },
                                        {
                                            id: "6",
                                            groupingId: 3,
                                            name: "ROUNDING_ADAPTATION",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 0.01,
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
            transactionTotal: -29,
        };
        // Check that the input is correctly generated with the discount
        // applied on the Business Menu All-In and its subproducts
        const thirdInput = getBlackboxOrderSign(order);

        expectTransactionTotals(thirdInput.transaction, order.currency);
        expect(thirdInput.transaction).toEqual(thirdInputData);

        const fourthInputData = {
            transactionLines: [
                {
                    lineType: "COMPOSITE_PRODUCT",
                    mainProduct: {
                        productId: "product_id_17",
                        productName: "Business Menu All-In",
                        departmentId: "11",
                        departmentName: "Menu",
                        quantity: -3,
                        quantityType: "PIECE",
                        unitPrice: 58,
                        vats: [],
                        negQuantityReason: "CORRECTION",
                    },
                    lineTotal: -156.6,
                    subProducts: [
                        {
                            productId: "product_id_9",
                            productName: "Carpaccio Beef",
                            departmentId: "7",
                            departmentName: "Starters",
                            quantity: -3,
                            quantityType: "PIECE",
                            unitPrice: 20,
                            vats: [
                                {
                                    label: "B",
                                    price: -60,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 11.67,
                                        },
                                        {
                                            id: "4_10P",
                                            groupingId: 2,
                                            name: "DISCOUNT_10P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: 4.83,
                                        },
                                    ],
                                },
                            ],
                            negQuantityReason: "CORRECTION",
                        },
                        {
                            productId: "product_id_10",
                            productName: "Burger of the Chef",
                            departmentId: "9",
                            departmentName: "Main Dishes",
                            quantity: -3,
                            quantityType: "PIECE",
                            unitPrice: 28,
                            vats: [
                                {
                                    label: "B",
                                    price: -84,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 16.32,
                                        },
                                        {
                                            id: "4_10P",
                                            groupingId: 2,
                                            name: "DISCOUNT_10P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: 6.77,
                                        },
                                    ],
                                },
                            ],
                            negQuantityReason: "CORRECTION",
                        },
                        {
                            productId: "product_id_8",
                            productName: "Matching Wines",
                            departmentId: "6",
                            departmentName: "Wines",
                            quantity: -3,
                            quantityType: "PIECE",
                            unitPrice: 24,
                            vats: [
                                {
                                    label: "A",
                                    price: -72,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 14.01,
                                        },
                                        {
                                            id: "4_10P",
                                            groupingId: 2,
                                            name: "DISCOUNT_10P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: 5.8,
                                        },
                                    ],
                                },
                            ],
                            negQuantityReason: "CORRECTION",
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
                        quantity: -2,
                        quantityType: "PIECE",
                        unitPrice: 58,
                        vats: [],
                        negQuantityReason: "PRICE_CHANGE",
                    },
                    lineTotal: -104.4,
                    subProducts: [
                        {
                            productId: "product_id_9",
                            productName: "Carpaccio Beef",
                            departmentId: "7",
                            departmentName: "Starters",
                            quantity: -2,
                            quantityType: "PIECE",
                            unitPrice: 20,
                            vats: [
                                {
                                    label: "B",
                                    price: -40,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 7.78,
                                        },
                                        {
                                            id: "4_10P",
                                            groupingId: 2,
                                            name: "DISCOUNT_10P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: 3.22,
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
                            quantity: -2,
                            quantityType: "PIECE",
                            unitPrice: 28,
                            vats: [
                                {
                                    label: "B",
                                    price: -56,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 10.88,
                                        },
                                        {
                                            id: "4_10P",
                                            groupingId: 2,
                                            name: "DISCOUNT_10P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: 4.51,
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
                            quantity: -2,
                            quantityType: "PIECE",
                            unitPrice: 24,
                            vats: [
                                {
                                    label: "A",
                                    price: -48,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 9.34,
                                        },
                                        {
                                            id: "4_10P",
                                            groupingId: 2,
                                            name: "DISCOUNT_10P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: 3.87,
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
                        quantity: 2,
                        quantityType: "PIECE",
                        unitPrice: 58,
                        vats: [],
                    },
                    lineTotal: 92.8,
                    subProducts: [
                        {
                            productId: "product_id_9",
                            productName: "Carpaccio Beef",
                            departmentId: "7",
                            departmentName: "Starters",
                            quantity: 2,
                            quantityType: "PIECE",
                            unitPrice: 20,
                            vats: [
                                {
                                    label: "B",
                                    price: 40,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -7.78,
                                        },
                                        {
                                            id: "4_20P",
                                            groupingId: 4,
                                            name: "DISCOUNT_20P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: -6.44,
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
                            quantity: 2,
                            quantityType: "PIECE",
                            unitPrice: 28,
                            vats: [
                                {
                                    label: "B",
                                    price: 56,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -10.88,
                                        },
                                        {
                                            id: "4_20P",
                                            groupingId: 4,
                                            name: "DISCOUNT_20P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: -9.02,
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
                            quantity: 2,
                            quantityType: "PIECE",
                            unitPrice: 24,
                            vats: [
                                {
                                    label: "A",
                                    price: 48,
                                    priceChanges: [
                                        {
                                            id: "1",
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -9.34,
                                        },
                                        {
                                            id: "4_20P",
                                            groupingId: 4,
                                            name: "DISCOUNT_20P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: -7.73,
                                        },
                                        {
                                            id: "6",
                                            groupingId: 3,
                                            name: "ROUNDING_ADAPTATION",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -0.01,
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
            transactionTotal: -168.2,
        };
        // Remove one line and add more discounts to check that the input is correctly
        // generated with multiple corrections and discounts
        order.lines[0].setQuantity(2, true);
        store.setDiscountFromUI(order.lines[0], 20);
        const fourthInput = getBlackboxOrderSign(order);
        expectTransactionTotals(fourthInput.transaction, order.currency);
        expect(fourthInput.transaction).toEqual(fourthInputData);

        const fifthInputData = {
            transactionLines: [
                {
                    lineType: "COMPOSITE_PRODUCT",
                    mainProduct: {
                        negQuantityReason: "REFUND",
                        productId: "product_id_17",
                        productName: "Business Menu All-In",
                        departmentId: "11",
                        departmentName: "Menu",
                        quantity: -1,
                        quantityType: "PIECE",
                        unitPrice: 58,
                        vats: [],
                    },
                    lineTotal: -46.4,
                    subProducts: [
                        {
                            negQuantityReason: "REFUND",
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 3.89,
                                        },
                                        {
                                            id: "4_20P",
                                            groupingId: 4,
                                            name: "DISCOUNT_20P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: 3.22,
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            negQuantityReason: "REFUND",
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 5.44,
                                        },
                                        {
                                            id: "4_20P",
                                            groupingId: 4,
                                            name: "DISCOUNT_20P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: 4.51,
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            negQuantityReason: "REFUND",
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 4.67,
                                        },
                                        {
                                            id: "4_20P",
                                            groupingId: 4,
                                            name: "DISCOUNT_20P",
                                            scope: "LINE",
                                            type: "PUBLIC",
                                            amount: 3.87,
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
            transactionTotal: -46.4,
        };
        // Simulate refunds
        order.l10n_be_last_transaction_by_line = {};
        order.is_refund = true;
        order.lines[0].setQuantity(-1, true);
        const fifthInput = getBlackboxOrderSign(order);
        expectTransactionTotals(fifthInput.transaction, order.currency);
        expect(fifthInput.transaction).toEqual(fifthInputData);
    });

    test("Business Menu All-In with global discount", async () => {
        const store = await setupPosBlackboxEnv();
        store.addNewOrder();
        const order = store.getOrder();
        const comp = await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });
        await comp.addProductToOrder(store.models["product.template"].get(17));
        await store.applyDiscount(20);

        const firstInputData = {
            transactionLines: [
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
                    lineTotal: 46.4,
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -3.89,
                                        },
                                        {
                                            id: "2_20P",
                                            groupingId: 2,
                                            name: "GLOBAL_DISCOUNT_20P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: -3.22,
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -5.44,
                                        },
                                        {
                                            id: "2_20P",
                                            groupingId: 2,
                                            name: "GLOBAL_DISCOUNT_20P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: -4.51,
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -4.67,
                                        },
                                        {
                                            id: "2_20P",
                                            groupingId: 2,
                                            name: "GLOBAL_DISCOUNT_20P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: -3.87,
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
            transactionTotal: 46.4,
        };
        const firstInput = getBlackboxOrderSign(order);
        expect(firstInput.transaction).toEqual(firstInputData);
        expectTransactionTotals(firstInput.transaction, order.currency);

        // Add a line discount and check
        await store.setDiscountFromUI(order.lines[0], 10);
        await store.applyDiscount(20); // reapply the GD

        const secondInputData = {
            transactionLines: [
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
                    lineTotal: -46.4,
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 3.89,
                                        },
                                        {
                                            id: "2_20P",
                                            groupingId: 2,
                                            name: "GLOBAL_DISCOUNT_20P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: 3.22,
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 5.44,
                                        },
                                        {
                                            id: "2_20P",
                                            groupingId: 2,
                                            name: "GLOBAL_DISCOUNT_20P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: 4.51,
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: 4.67,
                                        },
                                        {
                                            id: "2_20P",
                                            groupingId: 2,
                                            name: "GLOBAL_DISCOUNT_20P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: 3.87,
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
                    lineTotal: 41.76,
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -3.89,
                                        },
                                        {
                                            id: "2_20P",
                                            groupingId: 2,
                                            name: "GLOBAL_DISCOUNT_20P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: -2.9,
                                        },
                                        {
                                            id: "4_10P",
                                            groupingId: 3,
                                            name: "DISCOUNT_10P",
                                            scope: "LINE",
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -5.44,
                                        },
                                        {
                                            id: "2_20P",
                                            groupingId: 2,
                                            name: "GLOBAL_DISCOUNT_20P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: -4.06,
                                        },
                                        {
                                            id: "4_10P",
                                            groupingId: 3,
                                            name: "DISCOUNT_10P",
                                            scope: "LINE",
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
                                            groupingId: 1,
                                            name: "MENU_DISCOUNT",
                                            scope: "LINE",
                                            type: "INTERNAL",
                                            amount: -4.67,
                                        },
                                        {
                                            id: "2_20P",
                                            groupingId: 2,
                                            name: "GLOBAL_DISCOUNT_20P",
                                            scope: "EVENT",
                                            type: "PUBLIC",
                                            amount: -3.48,
                                        },
                                        {
                                            id: "4_10P",
                                            groupingId: 3,
                                            name: "DISCOUNT_10P",
                                            scope: "LINE",
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
            transactionTotal: -4.64,
        };
        const secondInput = getBlackboxOrderSign(order);
        expect(secondInput.transaction).toEqual(secondInputData);
        expectTransactionTotals(secondInput.transaction, order.currency);
    });
});
