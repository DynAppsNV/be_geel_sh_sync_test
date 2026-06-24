import { registry } from "@web/core/registry";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

export class UC230SignSaleCorrection {
    static code = "UC230_signSale_Correction";
    static name = "signSaleCorrection";

    constructor(blackbox) {
        this.blackbox = blackbox;
    }

    async sign(order, inszOrBisNumber) {
        const generator = new InputGenerator({
            models: order.models,
            order: order,
            inszOrBisNumber: inszOrBisNumber,
        });

        return this.blackbox.sign(
            { order: order, formatted: generator.generateSignSaleInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name
        );
    }

    get mutation() {
        return `
            mutation UC230_signSale_Correction($data: SaleInput!, $training: Boolean! = false) {
                signSale(data: $data, isTraining: $training) {
                    posId
                    posFiscalTicketNo
                    posDateTime
                    terminalId
                    deviceId
                    fdmSwVersion
                    eventOperation
                    digitalSignature
                    shortSignature
                    verificationUrl
                    bufferCapacityUsed
                    fdmRef {
                        fdmId
                        fdmDateTime
                        eventLabel
                        eventCounter
                        totalCounter
                    }
                    vatCalc {
                        label
                        rate
                        taxableAmount
                        vatAmount
                        totalAmount
                        outOfScope
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
    .add(UC230SignSaleCorrection.name, UC230SignSaleCorrection);
