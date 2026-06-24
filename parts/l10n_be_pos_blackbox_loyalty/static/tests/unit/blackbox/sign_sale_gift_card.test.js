import { test, expect, describe } from "@odoo/hoot";
import {
    expectTransactionLine,
    setupPosBlackboxEnv,
    expectGeneralProperties,
    payOrder,
    expectFinancial,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { addProductLineToOrder } from "@pos_loyalty/../tests/unit/utils";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { onRpc } from "@web/../tests/web_test_helpers";

definePosModels();

const { DateTime } = luxon;

// see enterprise/l10n_be_pos_blackbox_loyalty/static/tests/unit/data/json/uc260_mpv_signSale.json
describe("sign_sale with a gift card", () => {
    test("check signSale request when selling a gift card", async () => {
        const store = await setupPosBlackboxEnv();
        const models = store.models;
        const order = store.addNewOrder();
        const giftProgram = models["loyalty.program"].get(33);
        const giftCardProduct = models["product.product"].get(100);

        await addProductLineToOrder(
            store,
            order,
            {
                price_unit: 100,
                productId: 100,
                templateId: 100,
            },
            { eWalletGiftCardProgram: giftProgram }
        );
        const expirationDate = DateTime.now().plus({ days: 1 }).toISODate();
        order.processGiftCard("GIFT_CODE", 100, expirationDate);

        payOrder(store, order);
        const response = await store.blackbox.signSale.sign(order, "1234567890");
        await store.syncAllOrders();
        const input = response.formatted;
        expectGeneralProperties(input, { order: order, ticketMedium: "DIGITAL" });

        const transactions = input.transaction.transactionLines;
        const financials = input.financials;

        expect(transactions).toHaveLength(1);
        expectTransactionLine(
            transactions[0],
            giftCardProduct,
            1,
            "PIECE",
            100,
            "X",
            "SINGLE_PRODUCT"
        );

        expect(financials).toHaveLength(1);
        expectFinancial(financials[0], "Cash", "PAYMENT", 100, "CASH");
    });

    test("check signSale request when selling a gift card with price change", async () => {
        const store = await setupPosBlackboxEnv();
        const models = store.models;
        const order = store.addNewOrder();
        const giftProgram = models["loyalty.program"].get(33);
        const giftCardProduct = models["product.product"].get(100);

        const line = await addProductLineToOrder(
            store,
            order,
            {
                price_unit: 100,
                productId: 100,
                templateId: 100,
            },
            { eWalletGiftCardProgram: giftProgram }
        );
        line.price_type = "manual";
        line.setUnitPrice(120); // set a price change

        const expirationDate = DateTime.now().plus({ days: 1 }).toISODate();
        order.processGiftCard("GIFT_CODE", 120, expirationDate);

        payOrder(store, order);
        const response = await store.blackbox.signSale.sign(order, "1234567890");
        await store.syncAllOrders();
        const input = response.formatted;
        expectGeneralProperties(input, {
            order: order,
            ticketMedium: "DIGITAL",
            mustHavePriceChanges: true,
        });

        const transactions = input.transaction.transactionLines;
        const financials = input.financials;

        expect(transactions).toHaveLength(1);
        expectTransactionLine(
            transactions[0],
            giftCardProduct,
            1,
            "PIECE",
            100,
            "X",
            "SINGLE_PRODUCT"
        );
        expect(transactions[0].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transactions[0].mainProduct.vats[0].priceChanges[0].scope).toBe("LINE");
        expect(transactions[0].mainProduct.vats[0].priceChanges[0].name).toBe("UNIT_PRICE_CHANGE");

        expect(financials).toHaveLength(1);
        expectFinancial(financials[0], "Cash", "PAYMENT", 120, "CASH");
    });

    test("check signSale request using a gift card", async () => {
        onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => false);

        const store = await setupPosBlackboxEnv();
        const models = store.models;
        const order = await getFilledOrder(store);
        const giftCardProduct = models["product.product"].get(100);
        const giftCardReward = models["loyalty.reward"].get(33);
        const chardonnay = models["product.product"].get(6);
        const bourgogne = models["product.product"].get(5);

        models["pos.order.line"].create({
            order_id: order.id,
            price_type: "manual",
            is_reward_line: true,
            reward_id: giftCardReward.id,
            product_id: giftCardProduct.id,
            qty: 1,
            price_unit: -50,
        });

        order.state = "paid";
        store.models["pos.payment"].create({
            amount: order.priceIncl - 50,
            pos_order_id: order,
            payment_method_id: store.models["pos.payment.method"].find((m) => m.name === "Cash"),
        });
        store.addPendingOrder([order.id]);

        const response = await store.blackbox.signSale.sign(order, "1234567890");
        const input = response.formatted;
        expectGeneralProperties(input, { order: order, ticketMedium: "DIGITAL" });

        const transactions = input.transaction.transactionLines;
        const financials = input.financials;

        expect(transactions).toHaveLength(2);
        expectTransactionLine(transactions[0], bourgogne, 3, "PIECE", 35, "A", "SINGLE_PRODUCT");
        expectTransactionLine(transactions[1], chardonnay, 2, "PIECE", 40, "A", "SINGLE_PRODUCT");

        expect(financials).toHaveLength(2);
        expectFinancial(financials[0], "Cash", "PAYMENT", 85, "CASH");
        expectFinancial(financials[1], "Gift Card Redemption", "PAYMENT", 50, "VOUCHER_STORE");
    });
});
