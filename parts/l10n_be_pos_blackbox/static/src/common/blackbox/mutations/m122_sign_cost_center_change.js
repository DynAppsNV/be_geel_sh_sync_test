import { registry } from "@web/core/registry";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

export class M122SignCostCenterChange {
    static code = "M122_signCostCenterChange";
    static name = "signCostCenterChange";

    constructor(blackbox) {
        this.blackbox = blackbox;
    }

    /***
     *  Used when lines are transferred to an empty order (like when doing split)
     */
    async signOrderChange(sourceOrder, destinationOrder, inszOrBisNumber) {
        const generator = new InputGenerator({
            models: sourceOrder.models,
            order: destinationOrder,
            sourceOrder: sourceOrder,
            inszOrBisNumber: inszOrBisNumber,
        });
        const res = await this.blackbox.sign(
            { formatted: generator.generateSignOrderChangeInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name
        );
        if (res) {
            sourceOrder.updateLastTransactionLines();
            destinationOrder.updateLastTransactionLines();
        }
        return res;
    }

    /**
     * Used when changing the cost center of an order without changing the lines (like when changing the table or the partner of an order)
     */
    async signCostCenterChange(order, oldCostCenter, newCostCenter, inszOrBisNumber) {
        const generator = new InputGenerator({
            models: order.models,
            order: order,
            inszOrBisNumber: inszOrBisNumber,
        });
        return await this.blackbox.sign(
            {
                formatted: generator.generateSignCostCenterChangeInput(
                    oldCostCenter,
                    newCostCenter
                ),
            },
            this.mutation,
            this.constructor.code,
            this.constructor.name
        );
    }

    get mutation() {
        return `
            mutation M122_signCostCenterChange($data: CostCenterChangeInput!, $training: Boolean! = false) {
                signCostCenterChange(data: $data, isTraining: $training) {
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

registry
    .category("l10n_be_pos_blackbox.mutations")
    .add(M122SignCostCenterChange.name, M122SignCostCenterChange);
