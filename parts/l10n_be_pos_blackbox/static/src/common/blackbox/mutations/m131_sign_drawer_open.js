import { registry } from "@web/core/registry";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

export class M131SignDrawerOpen {
    static code = "M131_signDrawerOpen";
    static name = "signDrawerOpen";

    constructor(blackbox) {
        this.blackbox = blackbox;
    }

    async sign(models, inszOrBisNumber) {
        const generator = new InputGenerator({
            models: models,
            inszOrBisNumber: inszOrBisNumber,
        });
        return this.blackbox.sign(
            { order: null, formatted: generator.generateDrawerOpenInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name
        );
    }

    get mutation() {
        return `
            mutation M131_signDrawerOpen($data: DrawerOpenInput!, $training: Boolean! = false) {
                signDrawerOpen(data: $data, isTraining: $training) {
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
    .add(M131SignDrawerOpen.name, M131SignDrawerOpen);
