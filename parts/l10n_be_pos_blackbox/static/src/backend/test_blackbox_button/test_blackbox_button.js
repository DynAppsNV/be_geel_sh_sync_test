import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

export class TestBlackboxButton extends Component {
    static template = `point_of_sale.TestBlackboxButton`;
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");
    }

    checkConfigAndCompanyData(posConfig, company) {
        if (!posConfig[0].establishment_number) {
            this.notification.add(
                _t(
                    "The %s config does not have an establishment number set. Please set it before testing the blackbox.",
                    posConfig[0].name
                ),
                { type: "danger" }
            );
            return false;
        }
        if (!posConfig[0].l10n_be_pos_id) {
            this.notification.add(
                _t(
                    "The %s config does not have a POS ID set. Please set it before testing the blackbox.",
                    posConfig[0].name
                ),
                { type: "danger" }
            );
            return false;
        }
        if (!company[0].vat) {
            this.notification.add(
                _t(
                    "The company %s does not have a VAT number set. Please set it before testing the blackbox.",
                    company[0].name
                ),
                { type: "danger" }
            );
            return false;
        }
        return true;
    }

    displayBlackboxUnreachableNotification(posConfig, error) {
        this.notification.add(
            _t(
                "Unable to reach the blackbox (for %s config). Please verify the IP address, network connectivity, and that the blackbox is online.",
                posConfig[0].name
            ),
            { type: "danger" }
        );
        console.error("Failed to connect to the blackbox:", error);
    }

    displayBlackboxErrorsNotification(posConfig, errors) {
        // If it's a graphql syntax error
        let errorMessage;
        if (errors.length === 1 && !("extensions" in errors[0])) {
            errorMessage = _t("Blackbox returned a syntax error:\n%s", errors[0].message);
        } else {
            // Otherwise, list all error codes returned by blackbox
            errorMessage = _t(
                "Blackbox returned some error(s) (for %s config):\n%s",
                posConfig[0].name,
                errors.map((error) => error.message).join(", ")
            );
        }
        this.notification.add(errorMessage, { type: "danger" });
        console.error("Blackbox errors:", errors);
    }

    async testSendBlackbox(configId, local_ip, use_lna) {
        const posConfig = await this.orm.read(
            "pos.config",
            [configId],
            ["company_id", "l10n_be_pos_id", "establishment_number", "name"]
        );
        const company = await this.orm.read(
            "res.company",
            [posConfig[0].company_id[0]],
            ["vat", "name"]
        );
        if (!this.checkConfigAndCompanyData(posConfig, company)) {
            return;
        }
        try {
            const protocol = use_lna ? "http:" : window.location.protocol;
            const response = await fetch(`${protocol}//${local_ip}/graphql`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                signal: AbortSignal.timeout(5000),
                body: this.getTestQueryBody(
                    posConfig[0].l10n_be_pos_id,
                    company[0].vat,
                    posConfig[0].establishment_number
                ),
            });
            const result = await response.json();
            if (response.ok) {
                if (result.errors) {
                    this.displayBlackboxErrorsNotification(posConfig, result.errors);
                    return;
                }
                this.notification.add(
                    _t("Successfully reached the blackbox (for %s config).", posConfig[0].name),
                    { type: "info" }
                );
            } else {
                if (result.errors) {
                    this.displayBlackboxErrorsNotification(posConfig, result.errors);
                    return;
                } else {
                    const error = new Error(
                        `HTTP Error, blackbox unreachable:  ${response.status} `
                    );
                    console.error("Failed to connect to the blackbox:", error);
                    throw error;
                }
            }
        } catch (error) {
            this.displayBlackboxUnreachableNotification(posConfig, error);
        }
    }

    async onClick() {
        if (this.props.record.dirty) {
            this.notification.add(_t("Please save the form before testing the blackbox."), {
                type: "danger",
            });
            return;
        }
        const data = this.props.record.data;
        const configs = data.pos_config_ids.resIds;
        if (configs.length === 0) {
            this.notification.add(
                _t("Please select at least one POS configuration to test the blackbox."),
                { type: "danger" }
            );
            return;
        }
        const local_ip = data.local_ip;
        if (!local_ip) {
            this.notification.add(
                _t("Please configure a valid local IP address in order to test the blackbox"),
                { type: "danger" }
            );
            return;
        }
        for (const configId of configs) {
            await this.testSendBlackbox(configId, local_ip, data.use_lna);
        }
    }

    getTestQueryBody(posId, vatNo, establishmentNumber) {
        return JSON.stringify({
            query: `
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
            `,
            variables: {
                data: {
                    language: "FR",
                    vatNo: vatNo,
                    estNo: establishmentNumber,
                    posId: posId,
                    posFiscalTicketNo: 1,
                    posDateTime: DateTime.now().toISO(),
                    posSwVersion: odoo.info?.server_version ?? "19.0+e",
                    terminalId: "Odoo-backend-test-btn",
                    deviceId: "8fe0063a-d470-4c49-a828-8fc848039984",
                    bookingPeriodId: "8fe0063a-d470-4c49-a828-8fc848039984",
                    bookingDate: DateTime.now().toISODate(),
                    employeeId: "00000000097",
                    ticketMedium: "NONE",
                },
                training: true,
            },
            operationName: "M140_signWorkIn",
        });
    }
}

export const TestBlackboxWidget = {
    component: TestBlackboxButton,
};
registry.category("view_widgets").add("l10n_be_pos_blackbox_test_button", TestBlackboxWidget);
