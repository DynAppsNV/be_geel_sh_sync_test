import { registry } from "@web/core/registry";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

export class M182signReportUserX {
    static code = "M182_signReportUserX";
    static name = "signReportUserX";

    constructor(blackbox) {
        this.blackbox = blackbox;
    }

    async signWithDelay(models, userData, inszOrBisNumber) {
        const generator = new InputGenerator({
            inszOrBisNumber: inszOrBisNumber,
            models: models,
            userData: userData,
        });
        return this.blackbox.signWithDelay(
            { order: null, formatted: generator.generateUserXInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name,
            { shouldBeClocked: false }
        );
    }

    get mutation() {
        return `
            mutation M182_signReportUserX($data: ReportUserXInput!, $training: Boolean! = false) {
                signReportUserX(data: $data, isTraining: $training) {
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
    .add(M182signReportUserX.name, M182signReportUserX);
