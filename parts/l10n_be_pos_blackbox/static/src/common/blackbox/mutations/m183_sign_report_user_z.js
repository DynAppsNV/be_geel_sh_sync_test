import { registry } from "@web/core/registry";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

export class M183signReportUserZ {
    static code = "M183_signReportUserZ";
    static name = "signReportUserZ";

    constructor(blackbox) {
        this.blackbox = blackbox;
    }

    async signWithDelay(models, userData, sessionId, inszOrBisNumber) {
        const generator = new InputGenerator({
            inszOrBisNumber: inszOrBisNumber,
            models: models,
            userData: userData,
        });
        return this.blackbox.signWithDelay(
            { sessionId: sessionId, formatted: generator.generateUserZInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name,
            { shouldBeClocked: false }
        );
    }

    get mutation() {
        return `
            mutation M183_signReportUserZ($data: ReportUserZInput!, $training: Boolean! = false) {
                signReportUserZ(data: $data, isTraining: $training) {
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
    .add(M183signReportUserZ.name, M183signReportUserZ);
