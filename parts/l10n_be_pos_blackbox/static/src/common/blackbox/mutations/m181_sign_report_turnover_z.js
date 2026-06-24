import { registry } from "@web/core/registry";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

export class M181signReportTurnoverZ {
    static code = "M181_signReportTurnoverZ";
    static name = "signReportTurnoverZ";

    constructor(blackbox) {
        this.blackbox = blackbox;
    }

    async signWithDelay(models, turnoverData, sessionId, inszOrBisNumber) {
        const generator = new InputGenerator({
            inszOrBisNumber: inszOrBisNumber,
            models: models,
            turnoverData: turnoverData,
        });
        return this.blackbox.signWithDelay(
            { sessionId: sessionId, formatted: generator.generateTurnoverZInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name,
            { shouldBeClocked: false }
        );
    }

    get mutation() {
        return `
            mutation M181_signReportTurnoverZ($data: ReportTurnoverZInput!, $training: Boolean! = false) {
                signReportTurnoverZ(data: $data, isTraining: $training) {
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
    .add(M181signReportTurnoverZ.name, M181signReportTurnoverZ);
