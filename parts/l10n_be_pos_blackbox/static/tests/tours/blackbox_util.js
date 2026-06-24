/* global posmodel */

import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as BlackboxOracle from "@l10n_be_pos_blackbox/../tests/tours/blackbox_oracle";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import { run } from "@point_of_sale/../tests/generic_helpers/utils";
const originalConsoleError = console.error;

export function startPosBlackbox() {
    return [
        BlackboxOracle.enableBlackboxOracle(),
        ...Chrome.startPoS(),
        Dialog.confirm("Open Register"),
    ];
}

export function endTour() {
    return [BlackboxOracle.disableBlackboxOracle(), Chrome.endTour()];
}

export function setCannotReachBackend() {
    return run(() => {
        // Override console.error to avoid failing tests due to expected connection lost errors
        console.error = (...args) => {
            const message = args[0] instanceof Error ? args[0].message : args[0];
            if (typeof message === "string" && message.includes("ConnectionLostError")) {
                console.info("Connection lost error handled in offline mode:", ...args);
            } else {
                originalConsoleError.apply(console, args);
            }
        };
        window.blackboxTestEnv.canReachBackend = false;
        window.dispatchEvent(new Event("offline"));
    }, "Backend reachable");
}

export function setCanReachBackend() {
    return run(() => {
        window.blackboxTestEnv.canReachBackend = true;
        window.dispatchEvent(new Event("online"));
    }, "Backend unreachable");
}

export function setCanReachBlackbox() {
    return run(() => {
        window.blackboxTestEnv.canReachBlackbox = true;
    }, "Blackbox reachable");
}

export function setCannotReachBlackbox() {
    // Override console.error to avoid failing tests due to expected blackbox unreachable errors
    console.error = (...args) => {
        const message = args[0] instanceof Error ? args[0].message : args[0];
        if (typeof message === "string" && message.includes("HTTP Error")) {
            console.info(message, ...args);
        } else {
            originalConsoleError.apply(console, args);
        }
    };
    return run(() => {
        window.blackboxTestEnv.canReachBlackbox = false;
    }, "Blackbox unreachable");
}

export function checkUserClockInStatus(status = "Clocked in") {
    return {
        content: `Check if the user clock-in status is (${status})`,
        trigger: `.cashier-name .clock-status[title="${status}"]`,
    };
}

export function confirmFdmErrorDialog() {
    return [Dialog.is({ title: "Network Error" }), Dialog.confirm("Ok")];
}

export function receiptContainsBlackboxData(expectedTicketVatLabel = "VAT TICKET") {
    return [
        FeedbackScreen.isShown(),
        Dialog.is({ title: "Printing Failed" }),
        Dialog.cancel(),
        {
            content: "Check that .blackbox-data contains all expected blackbox fields",
            trigger: "body",
            run: async () => {
                await BlackboxOracle.generateAndCheckTicket(
                    posmodel.getOrder(),
                    expectedTicketVatLabel
                );
            },
        },
    ];
}
