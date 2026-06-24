import { registry } from "@web/core/registry";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

export class M180signReportTurnoverX {
    static code = "M180_signReportTurnoverX";
    static name = "signReportTurnoverX";

    constructor(blackbox) {
        this.blackbox = blackbox;
    }

    async signWithDelay(models, turnoverData, inszOrBisNumber) {
        const generator = new InputGenerator({
            inszOrBisNumber: inszOrBisNumber,
            models: models,
            turnoverData: turnoverData,
        });
        return this.blackbox.signWithDelay(
            { order: null, formatted: generator.generateTurnoverXInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name,
            { shouldBeClocked: false }
        );
    }

    get mutation() {
        return `
            mutation M180_signReportTurnoverX($data: ReportTurnoverXInput!, $training: Boolean! = false) {
                signReportTurnoverX(data: $data, isTraining: $training) {
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
    .add(M180signReportTurnoverX.name, M180signReportTurnoverX);
