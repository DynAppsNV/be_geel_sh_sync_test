import { registry } from "@web/core/registry";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

export class M140SignWorkIn {
    static code = "M140_signWorkIn";
    static name = "signWorkIn";

    constructor(blackbox) {
        this.blackbox = blackbox;
    }

    async sign(models, inszOrBisNumber) {
        const generator = new InputGenerator({
            models: models,
            inszOrBisNumber: inszOrBisNumber,
        });
        return this.blackbox.sign(
            { order: null, formatted: generator.generateWorkInOutInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name
        );
    }

    get mutation() {
        return `
            mutation M140_signWorkIn($data: WorkInOutInput!, $training: Boolean! = false) {
                signWorkIn(data: $data, isTraining: $training) {
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

registry.category("l10n_be_pos_blackbox.mutations").add(M140SignWorkIn.name, M140SignWorkIn);
