import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { FDM_ERRORS } from "@l10n_be_pos_blackbox/common/blackbox/utils/fdm_traceback_message";
import { _t } from "@web/core/l10n/translation";

export const CONSOLE_COLOR = "#e92416ff";

// Custom Error class to handle errors returned by the Blackbox (FDM)
export class L10nBeBlackboxError extends Error {
    constructor(message, errors) {
        super(message);
        this.errors = errors;
        // Syntax error happen when the GraphQL request is malformed
        this.isSyntaxError =
            errors.length === 1 && (!errors[0].extensions || !errors[0].extensions.code);
        // Blackbox returns this error when the input data is not valid (for example 'transaction.transactionTotal != sum(transaction.transactionLines.lineTotal))'
        this.invalidInputError =
            errors.length === 1 && errors[0]?.extensions?.code === "INVALID_REQUEST";
        this.processErrors();
    }

    processErrors() {
        // If it's a graphql syntax error, it only contain one error without extensions & error code
        if (this.isSyntaxError) {
            logPosMessage("Blackbox Syntax Error", "sign", this.errors[0].message, CONSOLE_COLOR);
            this.errors[0].details = {
                message: _t(this.errors[0].message),
                code: "INVALID_SYNTAX",
                category: "FDM",
                path: "",
            };
        } else if (this.invalidInputError) {
            logPosMessage(
                "Blackbox Invalid Input Error",
                "sign",
                this.errors[0].message,
                CONSOLE_COLOR
            );
            this.errors[0].details = {
                message: _t(this.errors[0].message),
                code: "INVALID_INPUT",
                category: "FDM",
                path: "",
            };
        } else {
            for (const error of this.errors) {
                const errorCode = error.extensions.code;
                const fdmError = FDM_ERRORS[errorCode];
                if (errorCode && fdmError) {
                    error.details = {
                        message: fdmError.message,
                        code: error.extensions.code,
                        category: error.extensions.category,
                        path: error.path.join("/"),
                    };
                    logPosMessage(
                        "FDM Error",
                        "sign",
                        `[${errorCode}] ${fdmError.message}\n${JSON.stringify(error, null, 2)}`,
                        CONSOLE_COLOR
                    );
                } else {
                    error.details = {
                        message: error.message,
                        code: error.extensions?.code || "UNKNOWN_ERROR",
                        category: error.extensions?.category || "UNKNOWN_CATEGORY",
                    };

                    logPosMessage(
                        "Unknown FDM Error",
                        "sign",
                        JSON.stringify(error, null, 2),
                        CONSOLE_COLOR
                    );
                }
            }
        }
    }

    getMessage() {
        if (this.isSyntaxError) {
            return _t("A syntax error occurred while communicating with the FDM.");
        } else if (this.invalidInputError) {
            return _t(
                "The FDM rejected the data sent by the POS. Please check the data and try again."
            );
        }
        return this.errors
            .map((error) => (error.details ? error.details.message : error.message))
            .join("\n");
    }
}
