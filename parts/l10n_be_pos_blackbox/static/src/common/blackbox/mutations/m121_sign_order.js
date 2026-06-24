import { registry } from "@web/core/registry";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

export class M121SignOrder {
    static code = "M121_signOrder";
    static name = "signOrder";

    constructor(blackbox) {
        this.blackbox = blackbox;
        this.processing = false;
    }

    /**
     * This method is a wrapper for other methods to wait for the processing flag to be true before executing.
     */
    async _withProcessingGuard(fn) {
        if (this.processing) {
            await new Promise((resolve) => setTimeout(resolve, 300)); // Wait for 300ms before retrying, this can be changed if needed.
            return this._withProcessingGuard(fn);
        }
        try {
            this.processing = true;
            return await fn();
        } finally {
            this.processing = false;
        }
    }

    /**
     *  signOrder mutation work as follow:
     *  - Instead of sending whole order each time, the signOrder mutation should only send
     *      - New lines (not send yet to blackbox)
     *      - Updated lines (lines that have been modified) -> so we need to make correction for them (delete old line and add new line with new values)
     *      - Deleted lines (lines that have been deleted) -> so we need to make correction for them (delete old line)
     *  - If there is no transaction changes since the last time, don't do anything
     */
    async sign(order, inszOrBisNumber) {
        return this._withProcessingGuard(async () => {
            if (order.uiState.isBeingSplitted) {
                // During the splitting process, we don't want to trigger any signOrder correction
                return;
            }
            const generator = new InputGenerator({
                models: order.models,
                order: order,
                inszOrBisNumber: inszOrBisNumber,
            });

            const formattedInput = generator.generateSignOrderInput();
            if (formattedInput.transaction.transactionLines.length === 0) {
                // If there is no line to send, we can skip the signing
                return;
            }
            const result = await this.blackbox.sign(
                { order: order, formatted: formattedInput },
                this.mutation,
                this.constructor.code,
                this.constructor.name
            );
            return result;
        });
    }

    async signCanceledOrder(order, inszOrBisNumber) {
        return this._withProcessingGuard(async () => {
            const generator = new InputGenerator({
                models: order.models,
                order: order,
                inszOrBisNumber: inszOrBisNumber,
            });

            const formattedInput = generator.generateSignCanceledOrderInput();
            if (formattedInput.transaction.transactionLines.length === 0) {
                // If there is no line to send, we can skip the signing
                return;
            }
            const result = await this.blackbox.sign(
                { order: order, formatted: formattedInput, inszOrBisNumber: inszOrBisNumber },
                this.mutation,
                this.constructor.code,
                this.constructor.name
            );
            return result;
        });
    }

    async signGlobalDiscountChange(order, transLines, sourceLinesNextUuidMap, inszOrBisNumber) {
        return this._withProcessingGuard(async () => {
            const generator = new InputGenerator({
                models: order.models,
                order: order,
                inszOrBisNumber: inszOrBisNumber,
            });

            const formattedInput = generator.generateSignGlobalDiscountChangeInput(
                transLines,
                sourceLinesNextUuidMap
            );
            const result = await this.blackbox.sign(
                { order: order, formatted: formattedInput, inszOrBisNumber: inszOrBisNumber },
                this.mutation,
                this.constructor.code,
                this.constructor.name
            );
            return result;
        });
    }

    /**
     * Used when splitting an order (transferSplittedOrder) where the original order had a global
     * discount but the new split order does not inherit it. This corrects the transferred lines in
     * the blackbox by negating the GD-applied version (PRICE_CHANGE) and adding them back without GD.
     */
    async signSplitGlobalDiscountCorrection(
        order,
        transLines,
        sourceLinesNextUuidMap,
        inszOrBisNumber
    ) {
        return this._withProcessingGuard(async () => {
            const generator = new InputGenerator({
                models: order.models,
                order: order,
                inszOrBisNumber: inszOrBisNumber,
            });
            const formattedInput = generator.generateSignGlobalDiscountChangeInput(
                transLines,
                sourceLinesNextUuidMap,
                0 // targetGlobalDiscount = 0: the new split order has no global discount
            );
            if (formattedInput.transaction.transactionLines.length === 0) {
                return;
            }
            const result = await this.blackbox.sign(
                { order: order, formatted: formattedInput, inszOrBisNumber: inszOrBisNumber },
                this.mutation,
                this.constructor.code,
                this.constructor.name
            );
            return result;
        });
    }

    async signOrderWithCorrection(order, initialValues, inszOrBisNumber) {
        return this._withProcessingGuard(async () => {
            if (order.uiState.isBeingSplitted) {
                // During the splitting process, we don't want to trigger any signOrder correction
                return;
            }
            const generator = new InputGenerator({
                models: order.models,
                order: order,
                inszOrBisNumber: inszOrBisNumber,
            });
            const formattedInput = generator.generateSignOrderInput(initialValues);
            if (formattedInput.transaction.transactionLines.length === 0) {
                return;
            }
            const result = await this.blackbox.sign(
                { order: order, formatted: formattedInput, inszOrBisNumber: inszOrBisNumber },
                this.mutation,
                this.constructor.code,
                this.constructor.name
            );
            return result;
        });
    }

    get mutation() {
        return `
            mutation M121_signOrder($data: OrderInput!, $training: Boolean! = false) {
                signOrder(data: $data, isTraining: $training) {
                    posId
                    posFiscalTicketNo
                    posDateTime
                    terminalId
                    deviceId
                    fdmSwVersion
                    eventOperation
                    digitalSignature
                    bufferCapacityUsed
                    fdmRef {
                        fdmId
                        fdmDateTime
                        eventLabel
                        eventCounter
                        totalCounter
                    }
                    warnings {
                        message
                        locations {
                            line
                            column
                        }
                        extensions {
                            category
                            code
                            data {
                                name
                                value
                            }
                            showPos
                        }
                    }
                    informations {
                        message
                        locations {
                            line
                            column
                        }
                        extensions {
                            category
                            code
                            data {
                                name
                                value
                            }
                            showPos
                        }
                    }
                }
            }
        `;
    }
}

registry.category("l10n_be_pos_blackbox.mutations").add(M121SignOrder.name, M121SignOrder);
