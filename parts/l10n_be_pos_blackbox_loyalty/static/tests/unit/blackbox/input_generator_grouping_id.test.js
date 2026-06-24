import { test, describe, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("input generator loyalty groupingId", () => {
    const buildGenerator = (order) =>
        new InputGenerator({
            models: order.models,
            order,
            inszOrBisNumber: "1234567890",
        });

    const findPc = (priceChanges, name) => priceChanges.find((pc) => pc.name === name) ?? null;

    /**
     * Test groupingId 1 — Order-wide LOYALTY_DISCOUNT: all affected lines share
     * the same groupingId.
     *
     * The reward's identifier code is the same for every affected line, so
     * getLoyaltyGroupingId returns the same persistent ID for all of them.
     * Counter = 1 after generation (single allocation in initRewardsLineData).
     */
    test("[groupingId 1] order-wide LOYALTY_DISCOUNT: all affected lines share the same groupingId", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const models = store.models;
        const order = await getFilledOrder(store);

        const reward = models["loyalty.reward"].get(1);
        const loyalty_card = models["loyalty.card"].get(2);
        await store.orderUpdateLoyaltyPrograms();
        order._applyReward(reward, loyalty_card.id, { product: reward.reward_product_ids[0] });

        const input = buildGenerator(order).generateSignSaleInput();
        const transLines = input.transaction.transactionLines;

        expect(transLines).toHaveLength(2);
        const pc0 = findPc(transLines[0].mainProduct.vats[0].priceChanges, "LOYALTY_DISCOUNT");
        const pc1 = findPc(transLines[1].mainProduct.vats[0].priceChanges, "LOYALTY_DISCOUNT");
        expect(pc0).not.toBe(null);
        expect(pc1).not.toBe(null);
        // Same reward identifier code → same groupingId shared across all affected lines
        expect(pc0.groupingId).toBe(1);
        expect(pc1.groupingId).toBe(1);
        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(1);
    });

    /**
     * Test groupingId 2 — Loyalty groupingId is allocated lazily in
     * generatePriceChangeInput, AFTER the base price-change IDs of the line
     * that first triggers it.
     *
     * Expected allocation order:
     *   1  DISCOUNT_10P      (line 0 — allocated by base during generatePriceChangeInput)
     *   2  LOYALTY_DISCOUNT  (allocated on first encounter, after line 0's base IDs)
     *   3  DISCOUNT_10P      (line 1 — each line owns its own discount id)
     */
    test("[groupingId 2] loyalty groupingId allocated after base line-discount IDs", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const models = store.models;
        const order = await getFilledOrder(store);

        const reward = models["loyalty.reward"].get(1);
        const loyalty_card = models["loyalty.card"].get(2);
        await store.orderUpdateLoyaltyPrograms();
        order._applyReward(reward, loyalty_card.id, { product: reward.reward_product_ids[0] });

        // Add a 10% line discount to regular lines after the reward is applied
        for (const line of order.lines.filter((l) => !l.is_reward_line)) {
            line.discount = 10;
        }

        const input = buildGenerator(order).generateSignSaleInput();
        const transLines = input.transaction.transactionLines;

        expect(transLines).toHaveLength(2);
        const loyaltyPc = findPc(
            transLines[0].mainProduct.vats[0].priceChanges,
            "LOYALTY_DISCOUNT"
        );
        const discountPc = findPc(transLines[0].mainProduct.vats[0].priceChanges, "DISCOUNT_10P");

        // Line discount allocated first (base IDs come before loyalty)
        expect(discountPc.groupingId).toBe(1);
        // Loyalty ID allocated lazily after line 0's base IDs → greater than base
        expect(loyaltyPc.groupingId).toBe(2);
        // Two product lines × one discount each = counter 3 (2 line discounts + 1 loyalty)
        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(3);
    });

    /**
     * Test groupingId 3 — Two distinct rewards get different groupingIds.
     *
     * Reward 1 (order-wide discount) and reward 2 (free product) have different
     * reward_identifier_codes, so each gets its own entry in state.loyaltyRewards
     * and a distinct ID from the shared counter.
     * Counter = 2 after generation.
     *
     * We test getLoyaltyGroupingId directly to avoid the complexity of combining
     * two rewards in a full signSale flow.
     */
    test("[groupingId 3] two distinct rewards get different groupingIds", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = await getFilledOrder(store);

        const generator = buildGenerator(order);

        // Simulate two reward lines with distinct identifier codes
        const idA = generator.getLoyaltyGroupingId("REWARD_CODE_A");
        const idB = generator.getLoyaltyGroupingId("REWARD_CODE_B");
        // Same code again → reuses the existing id, counter stays at 2
        const idAAgain = generator.getLoyaltyGroupingId("REWARD_CODE_A");

        // Different codes → different ids
        expect(idA).not.toBe(idB);
        // Same code → same id (stable across calls)
        expect(idAAgain).toBe(idA);
        // Exactly 2 ids allocated from the shared persistent counter
        expect(order.l10n_be_grouping_id.groupingIdCount).toBe(2);
    });
});
