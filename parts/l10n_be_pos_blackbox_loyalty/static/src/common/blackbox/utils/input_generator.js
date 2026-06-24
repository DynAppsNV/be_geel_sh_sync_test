import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";
import { patch } from "@web/core/utils/patch";
import { uuidv4 } from "@point_of_sale/utils";
import { roundCurrency } from "@point_of_sale/app/models/utils/currency";

/**
 * Handling of loyalty program when using the blackbox:
 * Gift cards:
 *  - When selling gift card, we need to send the gift card as a transactionLine with the total amount of the gift card and with a 0% VAT.
 *  - When redeeming a gift card, we need to send a financial with the total amount of the gift card and with type VOUCHER_STORE.
 *  - We also need to make sure that the gift card line is not sent as a transaction line to the blackbox, otherwise we will have a
 *    mismatch between the total of the transaction lines and the total of the order.
 * EWallets:
 *  - For eWallet rewards, we need to send the eWallet as a financial with the total amount of the eWallet and with type VOUCHER_OTHER.
 *  - We also need to make sure that the eWallet line is not sent as a transaction line to the blackbox, otherwise we will have a
 *    mismatch between the total of the transaction lines and the total of the order.
 * Discount reward:
 *  - For discount rewards, we need to send the discount as a price change on the transaction line(s) affected by the discount.
 *  - The amount of the discount should be sent as a negative amount, and is computed based on the reward's amount and the affected lines.
 * Product reward:
 *  - For product rewards, we need to send the rewarded product as a price change on the transaction line of the rewarded product.
 *  - The amount of the price change should be sent as a negative amount, and is computed based on the reward line price.

    TODO-manv FIXME: For the moment order with free product and global discount are causing issue (line discount & line price change could also cause issue for line with free product)
    We should handle the following case for orders with free products (use 'lineInfos.freeQty')

    CASE 1: global discount does not affect the transLine (all line is free)
    ------------------------------------------------------------------------
    signOrder1
        +1 Pen    (3€)
            pc: freeProduct (1 qty) (-3€)
        lineTotal: 0€

    -> add global discount

    signOrder2 (empty) cause GD does not impact price of order line

    CASE 2: global discount affect the transLine (need price change correction)
    ---------------------------------------------------------------------------
    signOrder1
        +2 pen (lineTotal: 3€)
            vat.prices = 6€
            pc: freeProduct (1 qty) (-3€)

    -> add global discount (50%)

    signOrder2
        -1 pen (lineTotal: -3€)
            vat.prices = -3€
            negReason "PRICE_CHANGE"
        +1 pen (lineTotal 1.5€)
            vat.prices = 3€
            pc: globalDiscount 50% (-1.5€)

    signSale:
        +2 pen (lineTotal: 1.5€)
            vat.prices = 6€
            pc: globalDiscount 50% (-1.5)
                freeProduct (1 qty) (-3€)

    CASE 3: add a line (which is not free)
    --------------------------------------
    signOrder1
        +1 Pen    (3€)
            pc: freeProduct (1 qty) (-3€)
        lineTotal: 0€

    -> add a pen (not free)

    signOrder2
        +1 Pen    (3€)
        lineTotal: 3€

    CASE 4: add a line (which is free)
    ----------------------------------
    signOrder1
        +1 Pen    (3€)
            pc: freeProduct (1 qty) (-3€)
        lineTotal: 0€

    -> add a pen (and the reward line is also incremented)

    signOrder1
        +1 Pen    (3€)
            pc: freeProduct (1 qty) (-3€)
        lineTotal: 0€
 */
patch(InputGenerator.prototype, {
    setup(params) {
        super.setup(...arguments);
        this.giftCardLines = this.order?.lines.filter(
            (line) =>
                line.is_reward_line && line.reward_id?.program_id?.program_type === "gift_card"
        );
        this.eWalletLines = this.order?.lines.filter(
            (line) => line.is_reward_line && line.reward_id?.program_id?.program_type === "ewallet"
        );
        this.giftCardTotal = this.giftCardLines?.length
            ? Math.abs(this.giftCardLines.reduce((total, line) => total + line.displayPrice, 0))
            : 0;
        this.eWalletTotal = this.eWalletLines?.length
            ? Math.abs(this.eWalletLines.reduce((total, line) => total + line.displayPrice, 0))
            : 0;
        this.orderLineRewardPriceChanges = {};
        this.initRewardsLineData();
    },
    getLoyaltyGroupingId(rewardIdentifierCode) {
        const state = this._getGroupingState();
        if (!state.loyaltyRewards) {
            state.loyaltyRewards = {};
        }
        if (state.loyaltyRewards[rewardIdentifierCode] === undefined) {
            state.loyaltyRewards[rewardIdentifierCode] = this._nextGroupingId();
        }
        return state.loyaltyRewards[rewardIdentifierCode];
    },
    pushRewardPriceChange(lineId, priceChange) {
        if (!this.orderLineRewardPriceChanges[lineId]) {
            this.orderLineRewardPriceChanges[lineId] = [];
        }
        this.orderLineRewardPriceChanges[lineId].push(priceChange);
    },
    /**
     * Filters and returns the lines from `affectedLines` that are not combo lines and have the same tax IDs as the given `rewardLine`.
     * This is used to determine which lines are affected by a loyalty reward based on their tax information,
     * ensuring that combo lines are excluded from the calculation (cause combo price changes are put in the subProducts, not in parent).
     */
    getRewardAffectedLines(rewardLine, affectedLines) {
        const isSameTax = (taxIds1, taxIds2) => {
            if (taxIds1.length !== taxIds2.length) {
                return false;
            }

            const sorted1 = [...taxIds1].sort((a, b) => a - b);
            const sorted2 = [...taxIds2].sort((a, b) => a - b);

            for (let i = 0; i < sorted1.length; i++) {
                if (sorted1[i] !== sorted2[i]) {
                    return false;
                }
            }

            return true;
        };
        const rewardTaxIds = rewardLine.tax_ids.length ? rewardLine.tax_ids.map((t) => t.id) : [];
        return affectedLines.filter(
            (line) =>
                line.combo_line_ids.length === 0 &&
                isSameTax(line.tax_ids.length ? line.tax_ids.map((t) => t.id) : [], rewardTaxIds)
        );
    },
    /**
     * Precompute price changes for loyalty rewards and store them in `orderLineRewardPriceChanges` to be used later when generating the input for the blackbox.
     * For discount rewards, it calculates the amount of the discount for each affected line based on the line's price and the total price of all affected lines, and stores a price change with the name "LOYALTY_DISCOUNT".
     * For product rewards, it stores a price change with the name "LOYALTY_FREE_PRODUCT" and the amount of the reward line for the line corresponding to the rewarded product.
     */
    initRewardsLineData() {
        const rewardsLines = this.order?.lines.filter((line) => line.is_reward_line);
        rewardsLines?.forEach((rewardLine) => {
            const reward = rewardLine.reward_id;
            if (
                reward.program_id.program_type === "gift_card" ||
                reward.program_id.program_type === "ewallet"
            ) {
                // We handle gift card and eWallet rewards inside 'generateFinancialsInput', so we don't need to do anything else here
                return;
            }
            if (reward.reward_type === "discount") {
                const rewardDiscountApplicability = reward.discount_applicability;
                let affectedLines = [];
                let scope = "LINE";
                if (rewardDiscountApplicability === "order") {
                    scope = "EVENT";
                    affectedLines.push(...this.order.lines.filter((l) => !l.is_reward_line));
                } else if (rewardDiscountApplicability === "cheapest") {
                    affectedLines.push(this.order._getCheapestLine(reward));
                } else if (rewardDiscountApplicability === "specific") {
                    affectedLines.push(...this.order._getSpecificDiscountableLines(reward));
                }
                affectedLines = affectedLines.filter(Boolean);
                if (affectedLines.length) {
                    const taxAffectedLines = this.getRewardAffectedLines(rewardLine, affectedLines);
                    const totalAmountTaxAffectedLines = this.order.currency.round(
                        taxAffectedLines.reduce((total, line) => total + line.blackboxPrice, 0)
                    );
                    const rewardAmount = rewardLine.priceIncl;
                    for (const taxAffectedLine of taxAffectedLines) {
                        const res = {
                            id: "7",
                            name: "LOYALTY_DISCOUNT",
                            programName: reward.program_id.name,
                            amount: this.order.currency.round(
                                (taxAffectedLine.blackboxPrice / totalAmountTaxAffectedLines) *
                                    rewardAmount,
                                this.order.currency
                            ),
                            scope: scope,
                            rewardIdentifierCode: rewardLine.reward_identifier_code,
                        };
                        this.pushRewardPriceChange(taxAffectedLine.id, res);
                    }
                }
            } else if (reward.reward_type === "product") {
                const affectedLine = this.order.lines.find(
                    (line) => line.product_id.id === rewardLine.rewarded_product_id.id
                );
                if (affectedLine) {
                    const res = {
                        id: "7",
                        name: "LOYALTY_FREE_PRODUCT",
                        programName: reward.program_id.name,
                        amount: rewardLine.priceIncl,
                        scope: "LINE",
                        rewardIdentifierCode: rewardLine.reward_identifier_code,
                        freeQty: rewardLine.qty,
                    };
                    this.pushRewardPriceChange(affectedLine.id, res);
                }
            }
        });
    },
    computeLoyaltyPriceChangeAmount(line, baseAmount, qty) {
        return roundCurrency((baseAmount / line.qty) * qty, this.order.currency);
    },
    generatePriceChangeInput(line, initPrice, { priceUnit, discount, globalDiscount, qty }) {
        const res = super.generatePriceChangeInput(...arguments);
        const rewardPriceChanges = this.orderLineRewardPriceChanges[line.id] || [];
        if (rewardPriceChanges.length) {
            for (const priceChange of rewardPriceChanges) {
                res.push({
                    id: priceChange.id,
                    groupingId: this.getLoyaltyGroupingId(priceChange.rewardIdentifierCode),
                    name: priceChange.name,
                    type: "PUBLIC",
                    amount: this.computeLoyaltyPriceChangeAmount(line, priceChange.amount, qty),
                    scope: priceChange.scope,
                });
            }
        }
        return res;
    },
    /**
     * Calculates the total amount for a transaction line, including any reward price changes.
     * If there are reward price changes associated with the line, their amounts are added to the base total (which is usually the line's price after other discounts) to get the final total for the line.
     * For combo lines, it aggregates the reward price changes from all combo lines to ensure that the total reflects the combined effect of rewards on the entire combo, rather than just the parent line.
     */
    getTransactionLineTotal(line, qty) {
        const res = super.getTransactionLineTotal(...arguments);
        const rewardPriceChanges = line.combo_line_ids.length
            ? line.combo_line_ids
                  .map((comboLineId) => this.orderLineRewardPriceChanges[comboLineId.id] || [])
                  .flat()
            : this.orderLineRewardPriceChanges[line.id] || [];
        // Exclude LOYALTY_FREE_PRODUCT: free qty is already handled by getLineActualQty in the
        // base implementation, so only discount-type rewards need to adjust the total here.
        const discountPriceChanges = rewardPriceChanges.filter(
            (pc) => pc.name !== "LOYALTY_FREE_PRODUCT"
        );
        if (discountPriceChanges.length) {
            const totalRewardAmount = discountPriceChanges.reduce(
                (total, priceChange) =>
                    total + this.computeLoyaltyPriceChangeAmount(line, priceChange.amount, qty),
                0
            );
            return roundCurrency(res + totalRewardAmount, this.order.currency);
        }
        return res;
    },
    generateFinancialsInput() {
        const res = super.generateFinancialsInput(...arguments);
        if (this.giftCardLines.length) {
            res.push({
                id: uuidv4(),
                name: "Gift Card Redemption",
                type: "VOUCHER_STORE",
                inputMethod: "MANUAL",
                amount: roundCurrency(this.giftCardTotal, this.order.currency),
                amountType: "PAYMENT",
            });
        }
        if (this.eWalletLines.length) {
            res.push({
                id: uuidv4(),
                name: "EWallet Redemption",
                type: "VOUCHER_OTHER",
                inputMethod: "MANUAL",
                amount: roundCurrency(this.eWalletTotal, this.order.currency),
                amountType: "PAYMENT",
            });
        }
        return res;
    },
    getTransactionTotal() {
        const total = super.getTransactionTotal(...arguments);
        return roundCurrency(total + this.giftCardTotal + this.eWalletTotal, this.order.currency);
    },
    _buildTransactionLineWithInfo(line, transLine) {
        const res = super._buildTransactionLineWithInfo(...arguments);
        // If the line have a free product reward, we store the free quantity
        const rewardPriceChanges = this.orderLineRewardPriceChanges[line.id] || [];
        if (rewardPriceChanges.length) {
            for (const priceChange of rewardPriceChanges) {
                if (priceChange.name === "LOYALTY_FREE_PRODUCT") {
                    res.lineInfos.freeQty = priceChange.freeQty;
                }
            }
        }
        return res;
    },
    getLineActualQty(line, qty) {
        const res = super.getLineActualQty(...arguments);
        // Deduce freeQty from reward price changes if present
        const rewardPriceChanges = this.orderLineRewardPriceChanges[line.id] || [];
        let freeQty = 0;
        for (const priceChange of rewardPriceChanges) {
            if (priceChange.name === "LOYALTY_FREE_PRODUCT" && priceChange.freeQty) {
                freeQty += priceChange.freeQty;
            }
        }
        return res - freeQty;
    },
});
