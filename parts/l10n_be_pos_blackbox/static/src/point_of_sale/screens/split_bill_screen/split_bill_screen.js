/** @odoo-module **/

import { SplitBillScreen } from "@pos_restaurant/app/screens/split_bill_screen/split_bill_screen";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";
import { patch } from "@web/core/utils/patch";

patch(SplitBillScreen.prototype, {
    async _createNewSplitOrder(originalOrder, newOrderName, curOrderUuid) {
        if (!this.pos.blackbox.isActive) {
            return super._createNewSplitOrder(...arguments);
        }

        // Capture the original GD and signed lines BEFORE calling super, because:
        // - super may delete fully-transferred lines from the originalOrder
        // - we need the last signed state to build the GD correction
        const originalGD = originalOrder.globalDiscountPc;
        const originalTransLines = originalOrder.l10n_be_last_transaction_by_line;
        const usr = this.pos.getCashier().l10n_be_insz_or_bis_number;

        // Build the correction plan for top-level lines that are being transferred
        // and were previously signed with a GD.
        // Only applies during a transfer (isTransferred=true): the new order will NOT
        // inherit the GD, so the blackbox needs a PRICE_CHANGE correction for those lines.
        const allTransferPlan = [];
        if (this.isTransferred && originalGD && originalTransLines) {
            const generator = new InputGenerator({
                models: originalOrder.models,
                order: originalOrder,
                inszOrBisNumber: usr,
            });
            for (const line of originalOrder.lines) {
                // Only process top-level lines (skip combo children) that are being transferred
                if (!this.qtyTracker[line.uuid] || line.combo_parent_id) {
                    continue;
                }
                const lastSignedEntry = originalTransLines[line.uuid];
                const transferredQty = this.qtyTracker[line.uuid];
                let entry = null;
                if (lastSignedEntry) {
                    const { lineInfos } = lastSignedEntry;
                    if (transferredQty === lineInfos.qty) {
                        // Full transfer: use the existing transLine as-is
                        entry = lastSignedEntry;
                    } else {
                        // Partial transfer: generate a fresh transLine for just the transferred
                        // portion (with the original GD) before super modifies the line qty.
                        const partialTransLine = generator.generateTransactionLine(line, {
                            priceUnit: lineInfos.priceUnit,
                            discount: lineInfos.discount,
                            globalDiscount: lineInfos.globalDiscount,
                            qty: transferredQty,
                        });
                        partialTransLine.lineTotal =
                            generator.computeTransactionLineTotal(partialTransLine);
                        entry = {
                            transLine: partialTransLine,
                            lineInfos: { ...lineInfos, qty: transferredQty },
                        };
                    }
                }
                // Include all transferred top-level lines in the plan to ensure correct
                // positional alignment with newOrder.lines after super is called.
                allTransferPlan.push({ originalUuid: line.uuid, entry });
            }
        }

        const newOrder = await super._createNewSplitOrder(...arguments);

        // If there are signed lines that need a GD correction, build the correction maps
        // by matching the original lines to the newly created lines in newOrder by position.
        if (allTransferPlan.length > 0) {
            const newTopLevelLines = newOrder.lines.filter((l) => !l.combo_parent_id);
            const filteredTransLines = {};
            const sourceLinesNextUuidMap = {};
            for (let i = 0; i < allTransferPlan.length; i++) {
                const { originalUuid, entry } = allTransferPlan[i];
                const newLine = newTopLevelLines[i];
                if (!newLine || !entry) {
                    continue;
                }
                filteredTransLines[originalUuid] = entry;
                sourceLinesNextUuidMap[originalUuid] = newLine.uuid;
            }
            if (Object.keys(filteredTransLines).length > 0) {
                // Correct the transferred lines on the original order's cost center:
                // negate the GD-applied versions (PRICE_CHANGE) and add them back without GD.
                await this.pos.blackbox.signOrder.signSplitGlobalDiscountCorrection(
                    originalOrder,
                    filteredTransLines,
                    sourceLinesNextUuidMap,
                    usr
                );
            }
        }

        await this.pos.blackbox.signCostCenterChange.signOrderChange(originalOrder, newOrder, usr);
        return newOrder;
    },
});
