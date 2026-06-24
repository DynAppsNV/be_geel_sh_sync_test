import { registry } from "@web/core/registry";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

export class M123SignPreBill {
    static code = "M123_signPreBill";
    static name = "signPreBill";

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
            { order: order, formatted: generator.generatePreBillInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name
        );
    }

    get mutation() {
        return `
            mutation M123_signPreBill($data: PreBillInput!, $training: Boolean! = false) {
                signPreBill(data: $data, isTraining: $training) {
                    posId
                    posFiscalTicketNo
                    posDateTime
                    terminalId
                    deviceId
                    fdmSwVersion
                    eventOperation
                    digitalSignature
                    verificationUrl
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

registry.category("l10n_be_pos_blackbox.mutations").add(M123SignPreBill.name, M123SignPreBill);
