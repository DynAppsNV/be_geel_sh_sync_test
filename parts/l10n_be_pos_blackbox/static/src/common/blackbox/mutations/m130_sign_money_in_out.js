import { registry } from "@web/core/registry";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

export class M130SignMoneyInOut {
    static code = "M130_signMoneyInOut";
    static name = "signMoneyInOut";

    constructor(blackbox) {
        this.blackbox = blackbox;
    }

    async sign(models, inszOrBisNumber, inOut, printerUrl) {
        const generator = new InputGenerator({
            models: models,
            moneyName: inOut.name,
            moneyAmount: inOut.amount,
            inszOrBisNumber: inszOrBisNumber,
            printerUrl: printerUrl,
        });
        return this.blackbox.sign(
            { order: null, formatted: generator.generateMoneyInOutInput() },
            this.mutation,
            this.constructor.code,
            this.constructor.name
        );
    }

    get mutation() {
        return `
            mutation M130_signMoneyInOut($data: MoneyInOutInput!, $training: Boolean! = false) {
                signMoneyInOut(data: $data, isTraining: $training) {
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
    .add(M130SignMoneyInOut.name, M130SignMoneyInOut);
