import { test, describe, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    getComboOrder,
    expectGeneralProperties,
    expectTransactionLine,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

definePosModels();

describe("input generator price consistency", () => {
    const generateOrderInput = (order) => {
        const generator = new InputGenerator({
            models: order.models,
            order: order,
            inszOrBisNumber: "1234567890",
        });
        return generator.generateSignSaleInput();
    };
    test("[case 1] test order with 10% discount loyalty", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const models = store.models;
        const order = await getFilledOrder(store);

        const reward = models["loyalty.reward"].get(1);
        const loyalty_card = models["loyalty.card"].get(2);
        const orderPrice = order.priceIncl;
        await store.orderUpdateLoyaltyPrograms();
        order._applyReward(reward, loyalty_card.id, { product: reward.reward_product_ids[0] });
        expect(order.priceIncl).toBeCloseTo(orderPrice * 0.9);

        const input = generateOrderInput(order);
        expectGeneralProperties(input, {
            order: order,
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });

        const transLines = input.transaction.transactionLines;
        expect(transLines).toHaveLength(2);
        expect(transLines[0].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].scope).toBe("EVENT");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].name).toBe("LOYALTY_DISCOUNT");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].amount).toBe(-10.5);
        expect(transLines[0].mainProduct.vats[0].price).toBe(105);

        expect(transLines[1].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transLines[1].mainProduct.vats[0].priceChanges[0].scope).toBe("EVENT");
        expect(transLines[1].mainProduct.vats[0].priceChanges[0].name).toBe("LOYALTY_DISCOUNT");
        expect(transLines[1].mainProduct.vats[0].priceChanges[0].amount).toBe(-8);
        expect(transLines[1].mainProduct.vats[0].price).toBe(80);
    });
    test("[case 2] test order with 10% discount loyalty with combo order", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const models = store.models;
        const order = await getComboOrder(store);

        const reward = models["loyalty.reward"].get(1);
        const loyalty_card = models["loyalty.card"].get(2);
        const menu = models["product.product"].find((m) => m.name === "Business Menu All-In");

        const orderPrice = order.priceIncl;
        await store.orderUpdateLoyaltyPrograms();
        order._applyReward(reward, loyalty_card.id, { product: reward.reward_product_ids[0] });
        expect(order.priceIncl).toBeCloseTo(orderPrice * 0.9);

        const input = generateOrderInput(order);
        expectGeneralProperties(input, {
            order: order,
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });

        const transLines = input.transaction.transactionLines;
        expect(transLines).toHaveLength(1);
        expectTransactionLine(transLines[0], menu, 1, "PIECE", 58, "A", "COMPOSITE_PRODUCT");
        expect(transLines[0].subProducts[0].vats[0].price).toBe(20);
        expect(transLines[0].subProducts[0].vats[0].priceChanges).toHaveLength(2);
        expect(transLines[0].subProducts[0].vats[0].priceChanges[0].name).toBe("MENU_DISCOUNT");
        expect(transLines[0].subProducts[0].vats[0].priceChanges[0].amount).toBe(-3.89);
        expect(transLines[0].subProducts[0].vats[0].priceChanges[1].name).toBe("LOYALTY_DISCOUNT");
        expect(transLines[0].subProducts[0].vats[0].priceChanges[1].amount).toBe(-1.61);
    });
    test("[case 3] test order with 10% discount loyalty with mixed order", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const models = store.models;
        const order = await getComboOrder(store, false, true);

        const reward = models["loyalty.reward"].get(1);
        const loyalty_card = models["loyalty.card"].get(2);
        const menu = models["product.product"].find((m) => m.name === "Business Menu All-In");

        const orderPrice = order.priceIncl;
        await store.orderUpdateLoyaltyPrograms();
        order._applyReward(reward, loyalty_card.id, { product: reward.reward_product_ids[0] });
        expect(order.priceIncl).toBeCloseTo(orderPrice * 0.9);

        const input = generateOrderInput(order);
        expectGeneralProperties(input, {
            order: order,
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });

        const transLines = input.transaction.transactionLines;
        expect(transLines).toHaveLength(2);
        expect(transLines[0].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].scope).toBe("EVENT");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].name).toBe("LOYALTY_DISCOUNT");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].amount).toBe(-0.61);
        expect(transLines[0].mainProduct.vats[0].price).toBe(6.08);

        expectTransactionLine(transLines[1], menu, 1, "PIECE", 58, "A", "COMPOSITE_PRODUCT");
        expect(transLines[1].subProducts[0].vats[0].price).toBe(20);
        expect(transLines[1].subProducts[0].vats[0].priceChanges).toHaveLength(2);
        expect(transLines[1].subProducts[0].vats[0].priceChanges[0].name).toBe("MENU_DISCOUNT");
        expect(transLines[1].subProducts[0].vats[0].priceChanges[0].amount).toBe(-3.89);
        expect(transLines[1].subProducts[0].vats[0].priceChanges[1].name).toBe("LOYALTY_DISCOUNT");
        expect(transLines[1].subProducts[0].vats[0].priceChanges[1].amount).toBe(-1.61);
    });
    test("[case 4] test order with 10% discount loyalty on cheapest product", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const models = store.models;
        const order = await getFilledOrder(store);
        order.lines.map((line) => (line.qty = 1));

        const reward = models["loyalty.reward"].get(1);
        reward.discount_applicability = "cheapest";
        const loyalty_card = models["loyalty.card"].get(2);

        const orderPrice = order.priceIncl;
        await store.orderUpdateLoyaltyPrograms();
        order._applyReward(reward, loyalty_card.id, { product: reward.reward_product_ids[0] });
        expect(orderPrice).toBe(75);
        expect(order.priceIncl).toBeCloseTo(72.11);

        const input = generateOrderInput(order);
        expectGeneralProperties(input, {
            order: order,
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });

        const transLines = input.transaction.transactionLines;
        expect(transLines).toHaveLength(2);
        expect(transLines[0].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].scope).toBe("LINE");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].name).toBe("LOYALTY_DISCOUNT");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].amount).toBe(-3.5);

        expect(transLines[1].mainProduct.vats[0].priceChanges).toHaveLength(0);
    });
    test("[case 5] test order with 10% discount loyalty on specific product", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const models = store.models;
        const order = await getFilledOrder(store);

        const reward = models["loyalty.reward"].get(1);
        reward.discount_applicability = "specific";
        reward.reward_product_ids = [];
        reward.all_discount_product_ids = [order.lines[1].product_id.product_tmpl_id];
        const loyalty_card = models["loyalty.card"].get(2);

        const orderPrice = order.priceIncl;
        await store.orderUpdateLoyaltyPrograms();
        order._applyReward(reward, loyalty_card.id, { product: reward.reward_product_ids[0] });
        expect(orderPrice).toBe(185);
        expect(order.priceIncl).toBeCloseTo(177);

        const input = generateOrderInput(order);
        expectGeneralProperties(input, {
            order: order,
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });

        const transLines = input.transaction.transactionLines;
        expect(transLines).toHaveLength(2);
        expect(transLines[0].mainProduct.vats[0].priceChanges).toHaveLength(0);

        expect(transLines[1].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transLines[1].mainProduct.vats[0].price).toBe(80);
        expect(transLines[1].mainProduct.vats[0].priceChanges[0].scope).toBe("LINE");
        expect(transLines[1].mainProduct.vats[0].priceChanges[0].name).toBe("LOYALTY_DISCOUNT");
        expect(transLines[1].mainProduct.vats[0].priceChanges[0].amount).toBe(-8);
    });
    test("[case 6] test order with free product", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const models = store.models;
        const order = await getFilledOrder(store);

        const reward = models["loyalty.reward"].get(34);
        const loyalty_card = models["loyalty.card"].get(2);
        expect(order.displayPrice).toBe(185);
        await store.orderUpdateLoyaltyPrograms();
        order._applyReward(reward, loyalty_card.id, {
            product: reward.reward_product_ids[0],
            quantity: 1,
        });
        const rewardLine = order?.lines.find((line) => line.is_reward_line);
        rewardLine.rewarded_product_id = reward.reward_product_ids[0];
        expect(order.displayPrice).toBe(150);

        const input = generateOrderInput(order);
        expectGeneralProperties(input, {
            order: order,
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });

        const transLines = input.transaction.transactionLines;
        expect(transLines).toHaveLength(2);
        expect(transLines[0].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transLines[0].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transLines[0].mainProduct.vats[0].price).toBe(105);
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].scope).toBe("LINE");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].name).toBe("LOYALTY_FREE_PRODUCT");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].amount).toBe(-35);
    });
    test("[case 7] test order with fully free product (qty=1): lineTotal should be 0", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const models = store.models;
        const order = await getFilledOrder(store);

        // Reduce qty of line 1 to 1 so the free-product reward covers it entirely
        order.lines[0].qty = 1;

        const reward = models["loyalty.reward"].get(34);
        const loyalty_card = models["loyalty.card"].get(2);
        await store.orderUpdateLoyaltyPrograms();
        order._applyReward(reward, loyalty_card.id, {
            product: reward.reward_product_ids[0],
            quantity: 1,
        });
        const rewardLine = order.lines.find((line) => line.is_reward_line);
        rewardLine.rewarded_product_id = reward.reward_product_ids[0];

        const input = generateOrderInput(order);
        expectGeneralProperties(input, {
            order,
            mustHavePriceChanges: true,
            ticketMedium: "DIGITAL",
        });

        const transLines = input.transaction.transactionLines;
        expect(transLines).toHaveLength(2);

        // The fully free line (qty=1, freeQty=1) must have lineTotal == 0
        expect(transLines[0].lineTotal).toBe(0);
        expect(transLines[0].mainProduct.vats[0].price).toBe(35);
        expect(transLines[0].mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].name).toBe("LOYALTY_FREE_PRODUCT");
        expect(transLines[0].mainProduct.vats[0].priceChanges[0].amount).toBe(-35);
    });
    test("[case 8] test order with fully free product and global discount: global discount must not affect free line", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const models = store.models;
        const order = await getFilledOrder(store);

        order.lines[0].qty = 1;

        const reward = models["loyalty.reward"].get(34);
        const loyalty_card = models["loyalty.card"].get(2);
        await store.orderUpdateLoyaltyPrograms();
        order._applyReward(reward, loyalty_card.id, {
            product: reward.reward_product_ids[0],
            quantity: 1,
        });
        const rewardLine = order.lines.find((line) => line.is_reward_line);
        rewardLine.rewarded_product_id = reward.reward_product_ids[0];

        // Simulate a 10% order-level global discount
        Object.defineProperty(order, "globalDiscountPc", { get: () => 10, configurable: true });

        const generator = new InputGenerator({
            models: order.models,
            order,
            inszOrBisNumber: "1234567890",
        });
        const transLinesMap = generator.generateTransactionLinesInput();
        const freeTransLine = Object.values(transLinesMap)
            .map(({ transLine }) => transLine)
            .find((tl) =>
                tl.mainProduct.vats[0]?.priceChanges?.some(
                    (pc) => pc.name === "LOYALTY_FREE_PRODUCT"
                )
            );

        // lineTotal must be 0: global discount has no room to apply on a fully free product
        expect(freeTransLine.lineTotal).toBe(0);
        // Only the LOYALTY_FREE_PRODUCT price change must be present — no GLOBAL_DISCOUNT
        expect(freeTransLine.mainProduct.vats[0].priceChanges).toHaveLength(1);
        expect(freeTransLine.mainProduct.vats[0].priceChanges[0].name).toBe("LOYALTY_FREE_PRODUCT");
        const globalDiscPc = freeTransLine.mainProduct.vats[0].priceChanges.find((pc) =>
            pc.name?.startsWith("GLOBAL_DISCOUNT")
        );
        expect(globalDiscPc).toBe(undefined);
    });
    test("[case 9] GD 50% on a line with qty=2 and 1 free: GD applies only to remaining 1 unit", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const models = store.models;
        const order = await getFilledOrder(store);

        // 2 units of product1 (price 35/unit), 1 will be free
        order.lines[0].qty = 2;

        // Apply 50% global discount FIRST so that orderUpdateLoyaltyPrograms (triggered
        // inside applyDiscount) runs while no reward is active yet, avoiding interference
        // with the manually-set rewarded_product_id below.

        const reward = models["loyalty.reward"].get(34);
        const loyalty_card = models["loyalty.card"].get(4);
        order._applyReward(reward, loyalty_card.id, {
            product: reward.reward_product_ids[0],
            quantity: 1,
        });
        const rewardLine = order.lines.find((line) => line.is_reward_line);
        rewardLine.rewarded_product_id = reward.reward_product_ids[0];
        await store.applyDiscount(50, order);

        const generator = new InputGenerator({
            models: order.models,
            order,
            inszOrBisNumber: "1234567890",
        });
        const transLinesMap = generator.generateTransactionLinesInput();
        const freeTransLine = Object.values(transLinesMap)
            .map(({ transLine }) => transLine)
            .find((tl) =>
                tl.mainProduct.vats[0]?.priceChanges?.some(
                    (pc) => pc.name === "LOYALTY_FREE_PRODUCT"
                )
            );

        // VAT base price spans the full 2 units at catalog price
        expect(freeTransLine.mainProduct.vats[0].price).toBe(70);

        // Exactly 2 price changes: GLOBAL_DISCOUNT_50P and LOYALTY_FREE_PRODUCT
        expect(freeTransLine.mainProduct.vats[0].priceChanges).toHaveLength(2);
        const gdPc = freeTransLine.mainProduct.vats[0].priceChanges.find((pc) =>
            pc.name?.startsWith("GLOBAL_DISCOUNT")
        );
        const freePc = freeTransLine.mainProduct.vats[0].priceChanges.find(
            (pc) => pc.name === "LOYALTY_FREE_PRODUCT"
        );

        // GD is applied to the 1 remaining (non-free) unit only: 35 * 50% = 17.5
        expect(gdPc.name).toBe("GLOBAL_DISCOUNT_50P");
        expect(gdPc.scope).toBe("EVENT");
        expect(gdPc.amount).toBe(-17.5);

        // Free product covers 1 unit at full price: -35
        expect(freePc.amount).toBe(-35);

        // lineTotal must equal VAT price + all priceChanges: 70 - 17.5 - 35 = 17.5
        expect(freeTransLine.lineTotal).toBe(17.5);
        expect(
            freeTransLine.mainProduct.vats[0].price +
                freeTransLine.mainProduct.vats[0].priceChanges.reduce(
                    (sum, pc) => sum + pc.amount,
                    0
                )
        ).toBe(freeTransLine.lineTotal);
    });
});
