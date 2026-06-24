import { registry } from "@web/core/registry";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

export class M110SignSale {
    static code = "M110_signSale";
    static name = "signSale";

    constructor(blackbox) {
        this.blackbox = blackbox;
    }

    async sign(order, inszOrBisNumber, printerUrl) {
        const generator = new InputGenerator({
            models: order.models,
            order: order,
            inszOrBisNumber: inszOrBisNumber,
            printerUrl: printerUrl,
        });

        return this.blackbox.sign(
            { order: order, formatted: generator.generateSignSaleInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name,
            { throwError: true }
        );
    }

    async signEmptyOrder(order, inszOrBisNumber, printerUrl) {
        const generator = new InputGenerator({
            models: order.models,
            order: order,
            inszOrBisNumber: inszOrBisNumber,
            printerUrl: printerUrl,
        });

        return this.blackbox.sign(
            { order: order, formatted: generator.generateSignSaleInput(true) },
            this.mutation,
            this.constructor.code,
            this.constructor.name,
            { throwError: true }
        );
    }

    get mutation() {
        return `
            mutation M110_signSale($data: SaleInput!, $training: Boolean! = false) {
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
                    footer
                }
            }
        `;
    }
}

registry.category("l10n_be_pos_blackbox.mutations").add(M110SignSale.name, M110SignSale);
