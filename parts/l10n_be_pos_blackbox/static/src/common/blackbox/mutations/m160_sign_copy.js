import { registry } from "@web/core/registry";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

export class M160SignCopy {
    static code = "M160_signCopy";
    static name = "signCopy";

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
            { order: order, formatted: generator.generateCopyInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name
        );
    }

    async signInvoice(order, inszOrBisNumber) {
        const generator = new InputGenerator({
            models: order.models,
            order: order,
            inszOrBisNumber: inszOrBisNumber,
        });

        return this.blackbox.sign(
            { order: order, formatted: generator.generateInvoiceCopyInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name
        );
    }

    async signReportWithDelay(models, reportFdmRef, inszOrBisNumber) {
        const generator = new InputGenerator({
            inszOrBisNumber: inszOrBisNumber,
            models: models,
            reportFdmRef: reportFdmRef,
        });
        return this.blackbox.signWithDelay(
            { formatted: generator.generateReportCopyInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name
        );
    }

    get mutation() {
        return `
            mutation M160_signCopy($data: CopyInput!, $training: Boolean! = false) {
                signCopy(data: $data, isTraining: $training) {
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

registry.category("l10n_be_pos_blackbox.mutations").add(M160SignCopy.name, M160SignCopy);
