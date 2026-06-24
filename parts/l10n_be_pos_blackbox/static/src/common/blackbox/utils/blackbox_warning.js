import { _t } from "@web/core/l10n/translation";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { FDM_WARNINGS } from "@l10n_be_pos_blackbox/common/blackbox/utils/fdm_traceback_message";

export const CONSOLE_COLOR = "#F5B427";

// Custom Warning class to handle and display warnings returned by the Blackbox (FDM)
export class L10nBeBlackboxWarning {
    static serviceDependencies = ["notification"];

    constructor(warning, { notification }) {
        this.warning = warning;
        this.code = warning.extensions.code;
        this.showPos = warning.extensions.showPos;
        this.notification = notification;
        this.processWarning();
    }

    processWarning() {
        const fdmWarning = FDM_WARNINGS[this.code];
        if (fdmWarning) {
            const showPoS = this.showPos;
            const show = showPoS === "MANDATORY" || (showPoS === "OPTIONAL" && fdmWarning.showPos);
            if (show) {
                this.notification.add(fdmWarning.message, { type: "warning" });
            }

            logPosMessage(
                "FDM Warning",
                "sign",
                `[${this.code}]: ${fdmWarning.message}.\n${JSON.stringify(this.warning)}`,
                CONSOLE_COLOR
            );
        } else {
            this.notification.add(_t("An unknown warning was received from the FDM."), {
                type: "warning",
            });

            logPosMessage(
                "Unknown FDM Warning",
                "sign",
                JSON.stringify(this.warning, null, 2),
                CONSOLE_COLOR
            );
        }
    }
}
