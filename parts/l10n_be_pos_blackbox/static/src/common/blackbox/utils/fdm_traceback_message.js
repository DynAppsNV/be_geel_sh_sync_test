import { _t } from "@web/core/l10n/translation";

export const FDM_WARNINGS = {
    CLIENT_CERT_NEAR_EXPIRATION: {
        showPos: true,
        message: _t("The client certificate will expire in less than 4 months."),
    },
    CLIENT_CERT_EXPIRED: {
        showPos: true,
        message: _t("The client certificate has expired."),
    },
    RTC_SYNC_FAILED: {
        showPos: false,
        message: _t("The FDM could not synchronize its real-time clock."),
    },
    UPDATE_URLS_FAILED: {
        showPos: false,
        message: _t("The FDM could not update its URLs."),
    },
    UPDATE_TRUST_CERT_FAILED: {
        showPos: false,
        message: _t("The FDM failed to update trust certificates."),
    },
    UPDATE_TASK_LIST_FAILED: {
        showPos: false,
        message: _t("The FDM could not download the task list."),
    },
    TASK_FEEDBACK_FAILED: {
        showPos: false,
        message: _t("The FDM could not report task feedback."),
    },
    NOP_FAILED: {
        showPos: false,
        message: _t("The FDM could not post a NOP message."),
    },
    BUFFER_NEAR_FULL: {
        showPos: true,
        message: _t("The FDM buffer usage exceeds 70%."),
    },
    SERVER_CERT_RESOLVE_FAILED: {
        showPos: false,
        message: _t("The FDM could not resolve the server certificate."),
    },
    TRANSACTION_UPLOAD_FAILED: {
        showPos: false,
        message: _t("The FDM failed multiple times to upload transactions."),
    },
    INITIALIZATION_FAILED: {
        showPos: false,
        message: _t("The FDM initialization has failed."),
    },
    RTC_NOT_INITIALIZED: {
        showPos: false,
        message: _t("The FDM real-time clock is not synchronized."),
    },
    CORRUPT_RECORD_ENCOUNTERED: {
        showPos: false,
        message: _t("The FDM detected a corrupt transaction record."),
    },
    UPDATE_PARAMS_FAILED: {
        showPos: false,
        message: _t("The FDM could not update its parameters."),
    },
    UPDATE_CLIENT_CERT_FAILED: {
        showPos: false,
        message: _t("The FDM could not update the client certificate."),
    },
    UPDATE_VAT_RATES_FAILED: {
        showPos: false,
        message: _t("The FDM could not update VAT rates."),
    },
    UPDATE_POS_ALLOWLIST_FAILED: {
        showPos: false,
        message: _t("The FDM could not update the POS allowlist."),
    },
    DUPLICATE_REQUEST: {
        showPos: false,
        message: _t("The FDM received a duplicate request."),
    },
    UPDATE_POS_VATNO: {
        showPos: true,
        message: _t("The VAT number of the company does not match the one registered in the FDM."),
    },
    UPDATE_POS_ESTNO: {
        showPos: true,
        message: _t("The establishment number does not match the one registered in the FDM."),
    },
    UNDEFINED_OTHER: {
        showPos: false,
        message: _t("An unspecified warning was reported by the FDM."),
    },
};

export const FDM_ERRORS = {
    BUFFER_FULL: {
        message: _t("The FDM buffer is full. No further transactions can be processed."),
    },
    FDM_LOCKED: {
        message: _t("The FDM is locked and cannot process requests."),
    },
    TOO_MANY_MEMORY_ERRORS: {
        message: _t("The FDM has encountered too many memory errors."),
    },
    UNAUTHORIZED: {
        message: _t("The FDM rejected an unauthorized request."),
    },
    INVALID_REQUEST: {
        message: _t("The FDM could not process the request due to invalid data."),
    },
    INTERNAL_ERROR: {
        message: _t("The FDM encountered a technical error."),
    },
    UNDEFINED_ERROR: {
        message: _t("The FDM encountered an undefined error."),
    },
    FDM_NOT_OPERATIONAL: {
        message: _t("The FDM is not operational."),
    },
    UNKNOWN_POS: {
        message: _t("The POS is not authorized to communicate with the FDM."),
    },
    UNDEFINED_OTHER: {
        message: _t("An unspecified error was reported by the FDM."),
    },
    DUPLICATE_REQUEST: {
        message: _t("The FDM received a duplicate request."),
    },
};
