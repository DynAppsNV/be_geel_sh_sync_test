import { registry } from "@web/core/registry";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { L10nBeBlackboxWarning } from "@l10n_be_pos_blackbox/common/blackbox/utils/blackbox_warning";
import { L10nBeBlackboxError } from "@l10n_be_pos_blackbox/common/blackbox/utils/blackbox_error";
import { L10nBeBlackboxConnectionError } from "@l10n_be_pos_blackbox/common/blackbox/utils/blackbox_connection_error";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError } from "@web/core/network/rpc";
import { LocalStorageQueue } from "./utils/localstorage_queue";
import { InspectPopup } from "@l10n_be_pos_blackbox/common/components/popups/inspect_popup/inspect_popup";
import { roundCurrency } from "@point_of_sale/app/models/utils/currency";

const { DateTime } = luxon;
const CONSOLE_COLOR = "#62da56";
const BLACKBOX_SIGNATURE_QUEUE_KEY = "l10n_be_blackbox_signature_queue";

export class PosBlackboxBe {
    constructor() {
        this.setup(...arguments);
    }

    async setup({
        models,
        data,
        dialog,
        notification,
        ensureClockedInFunc,
        showBlackboxErrorPopupFunc,
        handleBlackboxSignatureFunc,
    }) {
        this.models = models;
        this.data = data;
        this.dialog = dialog;
        this.notification = notification;
        this.signatureQueue = new LocalStorageQueue(BLACKBOX_SIGNATURE_QUEUE_KEY);

        // Queues arn't stored in the local storage because in case of error
        // the PoS will retry the request/signature and we don't want to keep
        // retrying indefinitely if the error is not transient (ex: syntax error or invalid input)
        this.requestQueue = [];

        // These functions given as parameter, because it's handled differently
        // when using `PosBlackboxBe` class in POS or in Kiosk
        this.ensureClockedInFunc = ensureClockedInFunc;
        this.showBlackboxErrorPopupFunc = showBlackboxErrorPopupFunc;
        this.handleBlackboxSignatureFunc = handleBlackboxSignatureFunc;

        for (const Mutation of registry.category("l10n_be_pos_blackbox.mutations").getAll()) {
            this[Mutation.name] = new Mutation(this);
        }

        window.addEventListener("pos-network-online", this.processSignatureQueue.bind(this));
    }

    get session() {
        return this.models["pos.session"].getFirst();
    }

    get config() {
        return this.models["pos.config"].getFirst();
    }

    get blackbox() {
        return this.config.l10n_be_blackbox_be_id;
    }

    get isActive() {
        return Boolean(this.config.l10n_be_blackbox_be_id);
    }

    async processSignatureQueue() {
        const payload = this.signatureQueue.purge();
        if (!payload.length) {
            return true;
        }

        try {
            await this.handleBlackboxSignatureFunc(payload);
            return true;
        } catch {
            this.signatureQueue.push(...payload);
            return false;
        }
    }

    /**
     * @param {*} order - The order object to process.
     * @param {*} signature - The signature object returned by the FDM.
     * @description
     * This method processes the order with the signature received from the FDM.
     * It updates the order with the event label, event counter, total counter,
     * short signature, FDM ID, and FDM date time.
     */
    async processOrderWithSignature(order, signature) {
        if (!order) {
            // Since we queue the request, the order may not be available
            logPosMessage(
                "Blackbox",
                "processOrderWithSignature",
                "No order found to process with signature.",
                CONSOLE_COLOR
            );
            return;
        }
        if (signature.eventOperation === "ORDER") {
            order.l10n_be_last_transaction_by_line = order.uiState.transactionLinesMap;
        }
        if (signature.eventOperation === "COPY") {
            return this.setFdmRefSignatureUiState("COPY", order, signature);
        }
        if (signature.eventOperation === "PRE_BILL") {
            return this.setFdmRefSignatureUiState("PRE_BILL", order, signature);
        }
        if (signature.eventOperation === "INVOICE") {
            return await this.setFdmRefEventI(order, signature);
        }
        if (signature.eventOperation === "SALE") {
            order.l10n_be_vat_calc = signature.vatCalc;
            order.l10n_be_event_label = signature.fdmRef.eventLabel;
            order.l10n_be_event_counter = signature.fdmRef.eventCounter;
            order.l10n_be_total_counter = signature.fdmRef.totalCounter;
            order.l10n_be_fdm_id = signature.fdmRef.fdmId;
            order.l10n_be_fdm_date_time = DateTime.fromISO(signature.fdmRef.fdmDateTime);
            order.l10n_be_pos_id = signature.posId;
            order.l10n_be_terminal_id = signature.terminalId;
            order.l10n_be_device_id = signature.deviceId;
            order.l10n_be_pos_date_time = DateTime.fromISO(signature.posDateTime);
            order.l10n_be_verification_url = signature.verificationUrl;
            order.l10n_be_footer = signature.footer;
        }

        if (!this.config.l10n_be_training_mode && signature.shortSignature) {
            order.l10n_be_short_signature = signature.shortSignature;
        }
    }

    setFdmRefSignatureUiState(key, order, signature) {
        order.uiState[key] = {
            l10n_be_fdm_id: signature.fdmRef.fdmId,
            l10n_be_fdm_date_time: DateTime.fromISO(signature.fdmRef.fdmDateTime).toFormat(
                "yyyy-MM-dd HH:mm:ss"
            ),
            l10n_be_event_label: signature.fdmRef.eventLabel,
            l10n_be_event_counter: signature.fdmRef.eventCounter,
            l10n_be_total_counter: signature.fdmRef.totalCounter,
        };
    }

    async setFdmRefEventI(order, signature) {
        this.data.write("pos.order", [order.id], {
            l10n_be_I_event_label: signature.fdmRef.eventLabel,
            l10n_be_I_event_counter: signature.fdmRef.eventCounter,
            l10n_be_I_total_counter: signature.fdmRef.totalCounter,
            l10n_be_I_fdm_id: signature.fdmRef.fdmId,
            l10n_be_I_fdm_date_time: DateTime.fromISO(signature.fdmRef.fdmDateTime).toFormat(
                "yyyy-LL-dd HH:mm:ss"
            ),
        });
    }

    /**
     * @param {Array} data Formatted data.
     * @param {string} mutation - The GraphQL mutation to execute.
     * @param {string} code - The code for the mutation operation.
     * @param {string} name - The name of the field to extract from the response.
     *
     * @description
     * This method sends a request to the FDM to sign the provided data.
     * Every request that does not need to be awaited should use this method.
     */
    async signWithDelay(data, mutation, code, name, opts = {}) {
        logPosMessage(
            "Blackbox",
            name,
            `Queueing ${data.length} object(s) for signing`,
            CONSOLE_COLOR
        );

        const rawData = { formatted: data.formatted, sessionId: data.sessionId, order: data.order };
        this.requestQueue.push({ data: rawData, mutation, code, name, opts });
        this.processRequestQueue();
    }

    /**
     * Process the queue of requests to the FDM.
     * This method will process each item in the queue and send the request to the FDM.
     * If a request fails, it will be kept in the queue for later processing.
     */
    async processRequestQueue() {
        if (this.processingQueue) {
            await new Promise((resolve) => setTimeout(resolve, 2000));
            return this.processRequestQueue();
        }
        try {
            this.processingQueue = true;
            const errors = [];
            const batch = [...this.requestQueue];
            this.requestQueue = [];

            for (const item of batch) {
                const { data, mutation, code, name, opts } = item;
                try {
                    await this.sign(data, mutation, code, name, { ...opts, throwError: true });
                } catch (error) {
                    if (this.shouldRetryMutation(error)) {
                        errors.push(item);
                    }
                }
            }
            if (errors.length) {
                this.requestQueue.push(...errors);
            }
        } finally {
            this.processingQueue = false;
        }
    }

    shouldRetryMutation(error) {
        if (error instanceof L10nBeBlackboxError) {
            // Retry only generic blackbox errors
            // Hard failures like invalid input or syntax errors are not recoverable (will never succeed).
            const isHardFailure = error.invalidInputError || error.isSyntaxError;

            if (isHardFailure) {
                logPosMessage(
                    "Blackbox",
                    "shouldRetryMutation",
                    `Not retrying: ${error.invalidInputError ? "invalid input" : "syntax"} error`,
                    CONSOLE_COLOR,
                    [error]
                );
                return false;
            }

            return true;
        }

        logPosMessage(
            "Blackbox",
            "shouldRetryMutation",
            "Unknown error type, not retrying",
            CONSOLE_COLOR,
            [error]
        );
        return false;
    }

    /**
     * @returns {Promise<boolean>}
     * @description
     * Check the connection to the FDM by sending it a ping. When the
     * user no longer has an internet connection and can no longer reach
     * the Odoo server, the FDM may still be reachable.
     */
    async ping() {
        try {
            await this._sendRequest({}, "{ status{ device { fdmId } } }", false);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * @param {Array} data Formatted data.
     * @param {string} mutation - The GraphQL mutation to execute.
     * @param {string} code - The code for the mutation operation.
     * @param {string} name - The name of the field to extract from the response.
     * @returns {Promise<Array | Boolean>} - Returns a promise that resolves to an array of processed
     *
     * @description
     * This method sends a request to the FDM to sign the provided data.
     * Every request that needs to be awaited should use this method.
     */
    async sign(
        data,
        mutation,
        code,
        name,
        { responseName = name, throwError = false, shouldBeClocked = true } = {}
    ) {
        if (!data) {
            return false;
        }

        logPosMessage("Blackbox", name, `Start processing ${data.length} object(s)`, CONSOLE_COLOR);
        try {
            if (shouldBeClocked) {
                await this.ensureClockedInFunc(name);
            }

            const result = await this._sendRequest(data.formatted, mutation, code);
            const signature = result.data?.[responseName];

            if (location.search && location.search.includes("debug_blackbox")) {
                this.dialog.add(InspectPopup, {
                    request: data.formatted,
                    response: result.data,
                });
            }

            return this._processBlackboxSignature(signature, data, name, responseName);
        } catch (error) {
            if (data.order && !data.order.l10n_be_short_signature) {
                data.order.state = "draft";
            }
            if (error instanceof L10nBeBlackboxConnectionError) {
                this.dialog.closeAll();
                this.dialog.add(AlertDialog, {
                    title: _t("FDM Connection Error"),
                    body: _t(
                        "Unable to contact the Fiscal Data Module. Please check the connection.\n%s",
                        error.message
                    ),
                });
                return;
            }
            if (error instanceof L10nBeBlackboxError) {
                this.showBlackboxErrorPopupFunc(error, data, name);
            }
            logPosMessage(
                "Blackbox: ",
                name,
                ` mutation returned an error. Data: ${JSON.stringify(data.formatted, null, 2)}`,
                CONSOLE_COLOR
            );
            if (throwError) {
                throw error;
            }
            return false;
        }
    }

    /**
     * Processes the blackbox signature received, handling warnings,
     * updating orders and session data, and managing event counters as needed.
     *
     * @param {Object} signature - The signature object returned by the blackbox, possibly containing warnings and FDM reference data.
     * @param {Object} data - The data object related to the blackbox operation, including order, sessionId, and formatted transaction details.
     * @param {string} name - The name of the operation or request being processed.
     * @param {string} responseName - The name of the response, used to determine specific processing logic (e.g., "signReportTurnoverZ").
     * @returns {Object} The original data object, after processing.
     */
    async _processBlackboxSignature(signature, data, name, responseName) {
        if (!signature) {
            return data;
        }

        if (signature.warnings) {
            signature.warnings.forEach((warning) => {
                new L10nBeBlackboxWarning(warning, { notification: this.notification });
            });
        }

        // Some request (like work-in/out) are not linked to an order,
        // so we don't need to process the signature
        const order = data.order;
        if (order) {
            this.processOrderWithSignature(data.order, signature);
        }

        // Some fields must be updated in the backend like event counters
        // or fdm references for reports
        const isInvoice = signature.fdmRef.eventLabel === "I";
        const transactionTotal = data.formatted.transaction?.transactionTotal || 0;
        const amount = isInvoice
            ? roundCurrency(data.order.priceIncl, data.order.currency)
            : transactionTotal;
        const payload = {
            signature: signature,
            amount: amount,
            isSelfSession: data.sessionId ? data.sessionId == this.session.id : true,
            data: data.formatted,
        };

        try {
            await this.processSignatureQueue();
            await this.handleBlackboxSignatureFunc([payload]);
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                this.signatureQueue.push(payload);
                return;
            }

            throw error;
        }

        logPosMessage("Blackbox", name, `End processing successfully`, CONSOLE_COLOR);
        return data;
    }

    /**
     * Send a GraphQL request to the FDM.
     * @param {string} query - The GraphQL query.
     * @param {object} variables - The variables for the query.
     * @private
     * @returns {Promise<object>} - The response from the FDM.
     * @throws {Error} - Throws an error if the request fails or if the response
     */
    async _sendRequest(data, mutation, operation = "") {
        try {
            const query = mutation;
            const isTraining = this.config.l10n_be_training_mode;
            const variables = { data, training: isTraining };
            const protocol = this.blackbox.use_lna ? "http:" : window.location.protocol;
            const payload = { query, variables, operationName: operation };
            if (!operation) {
                delete payload.operationName;
            }

            const response = await fetch(`${protocol}//${this.blackbox.local_ip}/graphql`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                signal: AbortSignal.timeout(5000),
                body: JSON.stringify(payload),
            });

            return await this._handleResponse(response);
        } catch (error) {
            // Check if its a connection error
            const message = error.message || "";
            const isConErr = message.includes("Failed to fetch") || message.includes("HTTP Error");
            if (isConErr || error.name === "TimeoutError") {
                throw new L10nBeBlackboxConnectionError(error.message);
            }

            logPosMessage(
                "Blackbox",
                "_sendRequest",
                "Erreur lors de l'appel au FDM",
                CONSOLE_COLOR,
                [error]
            );

            throw error;
        }
    }

    /**
     * Handles the HTTP response from the blackbox service.
     * Parses the JSON response and throws a custom error if any errors are present.
     * Throws a generic error if the response is not OK and no specific errors are provided.
     *
     * @async
     * @param {Response} response - The fetch API Response object to handle.
     * @returns {Promise<Object>} The parsed JSON result if the response is successful and contains no errors.
     * @throws {L10nBeBlackboxError} If the response contains errors.
     * @throws {Error} If the response is not OK and no specific errors are provided.
     */
    async _handleResponse(response) {
        const result = await response.json();
        if (result.errors) {
            throw new L10nBeBlackboxError("Blackbox error", result.errors);
        }
        return result;
    }
}
