/* global posmodel */

import { run } from "@point_of_sale/../tests/generic_helpers/utils";
import { ConnectionLostError } from "@web/core/network/rpc";

const originalFetch = window.fetch;
const originalSend = XMLHttpRequest.prototype.send;

const getM140_signWorkInResponse = () =>
    `{
        "data": {
            "signWorkIn": {
                "posId": "CPOS0031234568",
                "posFiscalTicketNo": 1010,
                "posDateTime": "2024-07-29T15:50:39+02:00",
                "terminalId": "POS-2-REC",
                "deviceId": "80:1A:A6:75:66:FC",
                "eventOperation": "WORK_IN",
                "fdmRef": {
                    "fdmId": "FOD01000002",
                    "fdmDateTime": "2024-07-29T13:50:39Z",
                    "eventLabel": "S",
                    "eventCounter": 7,
                    "totalCounter": 30
                },
                "fdmSwVersion": "1.2.0",
                "bufferCapacityUsed": 0.25,
                "digitalSignature": "c7uwqjLZ+Wk+R8swA/KHilWp4qCPK4u1L6TGxuCOJbf7bY32Ra2G8NiI+TO9lFGNFTfU1UA/8HGiccVzMQrUcA==",
                "warnings":[],
                "informations": []
            }
        }
    }`;

const getM141_signWorkOutResponse = () =>
    `{
        "data": {
            "signWorkOut": {
                "posId": "CPOS0031234567",
                "posFiscalTicketNo": 1011,
                "posDateTime": "2024-07-29T15:59:39+02:00",
                "terminalId": "TER-1-BAR",
                "deviceId": "b54a614f-39cc-4a7b-bd9f-aa6b693d769c",
                "eventOperation": "WORK_OUT",
                "fdmRef": {
                    "fdmId": "FOD01000001",
                    "fdmDateTime": "2024-07-29T13:59:43Z",
                    "eventLabel": "S",
                    "eventCounter": 8,
                    "totalCounter": 61
                },
                "fdmSwVersion": "1.2.0",
                "bufferCapacityUsed": 0.25,
                "digitalSignature": "c7uwqjLZ+Wk+R8swA/KHilWp4qCPK4u1L6TGxuCOJbf7bY32Ra2G8NiI+TO9lFGNFTfU1UA/8HGiccVzMQrUcA==",
                "warnings": [],
                "informations": []
            }
        }
    }`;

const getM110_signSaleResponse = () =>
    `{
        "data": {
            "signSale": {
            "posId": "CPOS0031234567",
            "posFiscalTicketNo": 1000,
            "posDateTime": "2024-07-29T13:00:00+02:00",
            "terminalId": "TER-2-DIN",
            "deviceId": "1631678d-7a85-4ac3-b296-bb4565e873fe",
            "vatCalc": [
                {
                "label": "A",
                "rate": 21,
                "taxableAmount": 19.83,
                "vatAmount": 4.17,
                "totalAmount": 24.0,
                "outOfScope": false
                },
                {
                "label": "B",
                "rate": 12,
                "taxableAmount": 25.0,
                "vatAmount": 3.0,
                "totalAmount": 28.0,
                "outOfScope": false
                }
            ],
            "eventOperation": "SALE",
            "fdmRef": {
                "fdmId": "FOD01000001",
                "fdmDateTime": "2024-07-29T11:00:08Z",
                "eventLabel": "N",
                "eventCounter": 15,
                "totalCounter": 59
            },
            "fdmSwVersion": "1.2.0",
            "bufferCapacityUsed": 0.25,
            "digitalSignature": "c7uwqjLZ+Wk+R8swA/KHilWp4qCPK4u1L6TGxuCOJbf7bY32Ra2G8NiI+TO9lFGNFTfU1UA/8HGiccVzMQrUcA==",
            "shortSignature": "ca39a3ee5e6b4b0d3255bfef95601890afd80709",
            "verificationUrl": "https://gs2.be/",
            "warnings": [],
            "informations": null
            }
        }
    }`;

const getM111_signSale_RefundResponse = () =>
    `{
        "data": {
            "signSale": {
            "posId": "CPOS0031234567",
            "posFiscalTicketNo": 1001,
            "posDateTime": "2024-07-29T13:15:00+02:00",
            "terminalId": "TER-2-DIN",
            "deviceId": "1631678d-7a85-4ac3-b296-bb4565e873fe",
            "vatCalc": [
                {
                "label": "A",
                "rate": 21,
                "taxableAmount": -19.83,
                "vatAmount": -4.17,
                "totalAmount": -24.0,
                "outOfScope": false
                },
                {
                "label": "B",
                "rate": 12,
                "taxableAmount": -25.0,
                "vatAmount": -3.0,
                "totalAmount": -28.0,
                "outOfScope": false
                }
            ],
            "eventOperation": "SALE",
            "fdmRef": {
                "fdmId": "FOD01000001",
                "fdmDateTime": "2024-07-29T11:15:00Z",
                "eventLabel": "N",
                "eventCounter": 16,
                "totalCounter": 60
            },
            "fdmSwVersion": "1.2.0",
            "bufferCapacityUsed": 0.25,
            "digitalSignature": "c7uwqjLZ+Wk+R8swA/KHilWp4qCPK4u1L6TGxuCOJbf7bY32Ra2G8NiI+TO9lFGNFTfU1UA/8HGiccVzMQrUcA==",
            "shortSignature": "ca39a3ee5e6b4b0d3255bfef95601890afd80709",
            "verificationUrl": "https://gs2.be/",
            "warnings": [],
            "informations": null
            }
        }
    }`;

const getM121_signOrderResponse = () =>
    `{
        "data": {
            "signOrder": {
            "posId": "CPOS0031234567",
            "posFiscalTicketNo": 1003,
            "posDateTime": "2024-07-29T13:57:03+02:00",
            "terminalId": "TER-1-BAR ",
            "deviceId": "b54a614f-39cc-4a7b-bd9f-aa6b693d769c",
            "eventOperation": "ORDER",
            "fdmRef": {
                "fdmId": "FOD01000001",
                "fdmDateTime": "2024-07-29T11:57:12Z",
                "eventLabel": "P",
                "eventCounter": 22,
                "totalCounter": 53
            },
            "fdmSwVersion": "1.2.0",
            "bufferCapacityUsed": 0.25,
            "digitalSignature": "c7uwqjLZ+Wk+R8swA/KHilWp4qCPK4u1L6TGxuCOJbf7bY32Ra2G8NiI+TO9lFGNFTfU1UA/8HGiccVzMQrUcA==",
            "warnings": [],
            "informations": []
            }
        }
    }`;

const getM112_signSale_RefundPartialResponse = () =>
    `{
        "data": {
            "signSale": {
            "posId": "CPOS0031234567",
            "posFiscalTicketNo": 6603,
            "posDateTime": "2024-10-07T13:48:00+02:00",
            "terminalId": "TER-1-BAR",
            "deviceId": "b54a614f-39cc-4a7b-bd9f-aa6b693d769c",
            "vatCalc": [
                {
                "label": "A",
                "rate": 21,
                "taxableAmount": -7.4,
                "vatAmount": -1.56,
                "totalAmount": -8.96,
                "outOfScope": false
                },
                {
                "label": "B",
                "rate": 12,
                "taxableAmount": 8.93,
                "vatAmount": 1.07,
                "totalAmount": 10.0,
                "outOfScope": false
                }
            ],
            "eventOperation": "SALE",
            "fdmRef": {
                "fdmId": "FOD01000001",
                "fdmDateTime": "2024-10-07T11:48:09Z",
                "eventLabel": "N",
                "eventCounter": 18,
                "totalCounter": 62
            },
            "fdmSwVersion": "1.2.0",
            "bufferCapacityUsed": 0.25,
            "digitalSignature": "c7uwqjLZ+Wk+R8swA/KHilWp4qCPK4u1L6TGxuCOJbf7bY32Ra2G8NiI+TO9lFGNFTfU1UA/8HGiccVzMQrUcA==",
            "shortSignature": "ca39a3ee5e6b4b0d3255bfef95601890afd80709",
            "verificationUrl": "https://gs2.be/",
            "warnings": [],
            "informations": null
            }
        }
    }`;

const getM122_signCostCenterChangeResponse = () =>
    `{
        "data": {
            "signCostCenterChange": {
            "posId": "AAAAAA00000000",
            "posFiscalTicketNo": 69,
            "posDateTime": "2025-10-14T10:14:18.273+02:00",
            "terminalId": "6dcfb16f-b461-444a-8849-ec979beaa2ae",
            "deviceId": "963186ae-15d6-4ccf-bee5-87c9361cca87",
            "eventOperation": "COST_CENTER_CHANGE",
            "fdmRef": {
                "fdmId": "VCB01002601",
                "fdmDateTime": "2025-10-14T08:14:18Z",
                "eventLabel": "P",
                "eventCounter": 281,
                "totalCounter": 1132
            },
            "fdmSwVersion": "0.0.1",
            "digitalSignature": "Nn+9EZ6ejbVk1xR4FNSUYxN06uv/ybjZnrl5j6Dsn4dH29Qok/G0cpkWpCDK4Lx1wZOXNnKLnSPFISoDNvwwk2Qs5yckPKBBeBQvLd77kUHZwYLU8y2YM5La7BuRYhaP75uqPn3jhtSfxb7HwDXj6KpwXg0VJ8LyLsyXt2GamQsDIJEb6ySeJDytkigd7WzMEUgihjv6hn5NvHTYaQT8HsVbBK+qZ7QrGjwgoUowVwtXL5GjTxO5OmUnHNC1kJHJ3VSWT733SUb3tHaUFtZasmCJT/QfG2l77ChZaNMwH9vTIuzPoLLQuUSpOj7SSZvFH9IKwdtEGlTvvRyjS0kYVg==",
            "shortSignature": "",
            "verificationUrl": "",
            "vatCalc": null,
            "bufferCapacityUsed": 1.13,
            "warnings": null,
            "informations": null,
            "footer": []
            }
        }
    }`;

const getM30_signMoneyInOutResponse = () =>
    `{
        "posId": "AAAAAA00000000",
        "posFiscalTicketNo": 447,
        "posDateTime": "2025-10-31T14:30:59.470+01:00",
        "terminalId": "eca95a80-cfcc-41b7-8637-e0f1ee86723e",
        "deviceId": "74183dd5-35bc-4ebc-aace-8dfbfef993f8",
        "eventOperation": "MONEY_IN_OUT",
        "fdmRef": {
            "fdmId": "VCB01002601",
            "fdmDateTime": "2025-10-31T14:30:58+01:00",
            "eventLabel": "F",
            "eventCounter": 52,
            "totalCounter": 1948
        },
        "fdmSwVersion": "0.0.1",
        "digitalSignature": "jN9I/3UG5xnO2s/vt12SuiiKh+a1XXbDGO60S9I9BTgm2q+tYccZ5LtPvTtlZYwVMmf/wLQhith1oehcXj7GMBiTiItrfH/fpSfgWbCzy4rz5b0x/bheA23lwiz8AbgaQcy+KeBCijjUKtlT5bL96pJAokDNk58KdqvQpL7P/m6C6Yxrv13hk8P7TIZ8TuNaeRHKX0dLee+AdA3VBosc/H4kcwW/TDoUu6sNdSF7N7e9+jDq8O0vovz+RskskMkBBsv+FuKYMY8kLqrCClLo07wytouyTpySeTd7jg3ePVeGdYFAuC0EP749Q50NLwr2KO3/va7I9AWOob1e1yBALA==",
        "shortSignature": "",
        "verificationUrl": "",
        "vatCalc": null,
        "bufferCapacityUsed": 1.95,
        "warnings": null,
        "informations": null,
        "footer": []
    }`;

const getM150_signInvoiceResponse = () =>
    `{
        "data": {
            "signInvoice": {
                "posId": "CPOS0031234567",
                "posFiscalTicketNo": 1011,
                "posDateTime": "2024-07-29T15:59:39+02:00",
                "terminalId": "TER-1-BAR",
                "deviceId": "b54a614f-39cc-4a7b-bd9f-aa6b693d769c",
                "eventOperation": "INVOICE",
                "fdmRef": {
                    "fdmId": "FOD01000001",
                    "fdmDateTime": "2024-07-29T13:59:43Z",
                    "eventLabel": "I",
                    "eventCounter": 8,
                    "totalCounter": 61
                },
                "fdmSwVersion": "1.2.0",
                "bufferCapacityUsed": 0.25,
                "digitalSignature": "c7uwqjLZ+Wk+R8swA/KHilWp4qCPK4u1L6TGxuCOJbf7bY32Ra2G8NiI+TO9lFGNFTfU1UA/8HGiccVzMQrUcA==",
                "warnings": [],
                "informations": []
            }
        }
    }`;

const getM31_signDrawerOpenResponse = () =>
    `{
        "posId": "AAAAAA00000000",
        "posFiscalTicketNo": 447,
        "posDateTime": "2025-10-31T14:30:59.470+01:00",
        "terminalId": "eca95a80-cfcc-41b7-8637-e0f1ee86723e",
        "deviceId": "74183dd5-35bc-4ebc-aace-8dfbfef993f8",
        "eventOperation": "DRAWER_OPEN",
        "fdmRef": {
            "fdmId": "VCB01002601",
            "fdmDateTime": "2025-10-31T14:30:58+01:00",
            "eventLabel": "F",
            "eventCounter": 52,
            "totalCounter": 1948
        },
        "fdmSwVersion": "0.0.1",
        "digitalSignature": "jN9I/3UG5xnO2s/vt12SuiiKh+a1XXbDGO60S9I9BTgm2q+tYccZ5LtPvTtlZYwVMmf/wLQhith1oehcXj7GMBiTiItrfH/fpSfgWbCzy4rz5b0x/bheA23lwiz8AbgaQcy+KeBCijjUKtlT5bL96pJAokDNk58KdqvQpL7P/m6C6Yxrv13hk8P7TIZ8TuNaeRHKX0dLee+AdA3VBosc/H4kcwW/TDoUu6sNdSF7N7e9+jDq8O0vovz+RskskMkBBsv+FuKYMY8kLqrCClLo07wytouyTpySeTd7jg3ePVeGdYFAuC0EP749Q50NLwr2KO3/va7I9AWOob1e1yBALA==",
        "shortSignature": "",
        "verificationUrl": "",
        "vatCalc": null,
        "bufferCapacityUsed": 1.95,
        "warnings": null,
        "informations": null,
        "footer": []
    }`;

const getM181_signReportTurnoverZResponse = () =>
    `{
        "data": {
            "signReportTurnoverZ": {
            "posId": "AAAAAA00000000",
            "posFiscalTicketNo": 893,
            "posDateTime": "2025-11-25T11:37:06.479+01:00",
            "terminalId": "bf348d38-f898-4b4a-a7c9-1ed8ccb8135e",
            "deviceId": "5257dd48-a45c-4754-a7ec-519c6264e3d5",
            "eventOperation": "REPORT_TURNOVER_Z",
            "fdmRef": {
                "fdmId": "VCB01002601",
                "fdmDateTime": "2025-11-25T11:37:07+01:00",
                "eventLabel": "R",
                "eventCounter": 123,
                "totalCounter": 2919
            },
            "fdmSwVersion": "0.0.1",
            "digitalSignature": "TAq70W/jWRJKdnDMcNEn2Yohi6mqak1N7AhniC1/n9BW1t0a4/QIXklfnlsBU+swbwF+W44JKK3GTj9uQQmLneAMMfFY+VTSqnysthE0oY3m19S1Bektr37wyFht+HkPkvu17qe6vTWiTUX5FF3A+Jml46eLnsz1HMQ6ecrfjUI/7C0Klo5mwL7w5XrCKHAlj+Q6/L8hTuUOzsCW0093CFutgA2sLRf9kl728MHgrra90/9qa8mHk0i7I9DYarjj/s8wh8FqlRFd9QS1CMX84lUS7xKcC0gg5cPb5h1IB6uPMGlcpVMdX/cko3FCiWYvxIk3SbuZ47B0H3HXs3tUaA==",
            "shortSignature": "",
            "verificationUrl": "",
            "vatCalc": null,
            "bufferCapacityUsed": 2.92,
            "warnings": null,
            "informations": null,
            "footer": []
            }
        }
    }`;

const getM183_signReportUserZResponse = () =>
    `{
        "data": {
            "signReportUserZ": {
            "posId": "AAAAAA00000000",
            "posFiscalTicketNo": 894,
            "posDateTime": "2025-11-25T11:37:06.481+01:00",
            "terminalId": "bf348d38-f898-4b4a-a7c9-1ed8ccb8135e",
            "deviceId": "5257dd48-a45c-4754-a7ec-519c6264e3d5",
            "eventOperation": "REPORT_USER_Z",
            "fdmRef": {
                "fdmId": "VCB01002601",
                "fdmDateTime": "2025-11-25T11:37:09+01:00",
                "eventLabel": "R",
                "eventCounter": 124,
                "totalCounter": 2920
            },
            "fdmSwVersion": "0.0.1",
            "digitalSignature": "N+z1OP5o7VzUMj7SRTWrkX5lHl0P9oOYU5kqUo8ntXAinUmtXnApDoaU5/9Gc3iJythmrq+gYr7EdcUekKqaiAAwSDgGX0akRC9GUDj8hWWdyY+XccLxqVdt7MHtV8Q7LmTkQkbXzONVchuSKGfzYxLGKMz6hbTOXqBTcCPglQEXK74utTdVrea2rwdhtC6SsgpR1FhJ+QkQH1IG8JT9hF+i55KZEG7TMyR90w2dAlKqE7WWrivLoy2thzkRbM7ysPePkCOwbS7BOQpq7Rt1kmHbBZ4miJQ+VsoW2ob/dP3hZwwvEjgzh6opPMV54drAc4TUwR6TE/0QFI0cLR/hfw==",
            "shortSignature": "",
            "verificationUrl": "",
            "vatCalc": null,
            "bufferCapacityUsed": 2.92,
            "warnings": null,
            "informations": null,
            "footer": []
            }
        }
    }`;

const mutationsResponse = {
    M140_signWorkIn: getM140_signWorkInResponse(),
    M141_signWorkOut: getM141_signWorkOutResponse(),
    M110_signSale: getM110_signSaleResponse(),
    M111_signSale_Refund: getM111_signSale_RefundResponse(),
    M112_signSale_RefundPartial: getM112_signSale_RefundPartialResponse(),
    M121_signOrder: getM121_signOrderResponse(),
    M122_signCostCenterChange: getM122_signCostCenterChangeResponse(),
    M130_signMoneyInOut: getM30_signMoneyInOutResponse(),
    M150_signInvoice: getM150_signInvoiceResponse(),
    M131_signDrawerOpen: getM31_signDrawerOpenResponse(),
    M181_signReportTurnoverZ: getM181_signReportTurnoverZResponse(),
    M183_signReportUserZ: getM183_signReportUserZResponse(),
};

export function enableBlackboxOracle() {
    return run(() => {
        // Initialize the request counter for each mutation, so we can check how many times each was called during the tour
        window.blackboxRequestCounter = Object.fromEntries(
            Object.keys(mutationsResponse).map((key) => [key, 0])
        );
        // Control whether we are online (can contact backend) and canReachBlackbox (can contact blackbox device)
        window.blackboxTestEnv = {
            canReachBackend: true,
            canReachBlackbox: true,
        };
        window.fetch = async (input, init = {}) => {
            try {
                const url = typeof input === "string" ? input : input.url;
                // Intercept blackbox GraphQL requests
                if (url.endsWith("/graphql") && init.body) {
                    if (!window.blackboxTestEnv.canReachBlackbox) {
                        throw new Error(`HTTP Error, blackbox unreachable`);
                    }
                    const bodyStr = init.body.toString();
                    let mutationFound = false;

                    if (bodyStr.includes("{ status{ device { fdmId } } }")) {
                        return Promise.resolve(
                            new Response(`{"data":{"status":{"device":{"fdmId":"VCB01002601"}}}}`, {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            })
                        );
                    }
                    for (const key of Object.keys(mutationsResponse)) {
                        if (bodyStr.includes(key)) {
                            mutationFound = true;
                            window.blackboxRequestCounter[key]++;
                            const mockResponse = mutationsResponse[key];
                            return Promise.resolve(
                                new Response(mockResponse, {
                                    status: 200,
                                    headers: { "Content-Type": "application/json" },
                                })
                            );
                        }
                    }
                    if (!mutationFound) {
                        console.info(
                            "Blackbox Oracle: No matching mutation found following request:",
                            bodyStr
                        );
                        //Don't FW the request if no mutation is found
                        return Promise.resolve(
                            new Response(
                                JSON.stringify({
                                    errors: [
                                        {
                                            message: "No matching mutation found in Oracle",
                                        },
                                    ],
                                }),
                                {
                                    status: 400,
                                    headers: { "Content-Type": "application/json" },
                                }
                            )
                        );
                    }
                } else {
                    if (!window.blackboxTestEnv.canReachBackend) {
                        throw new ConnectionLostError();
                    }
                }
            } catch (error) {
                console.info("Blackbox Oracle interception failed:", error);
                throw error;
            }
            return originalFetch.apply(this, arguments);
        };
        XMLHttpRequest.prototype.send = function (body) {
            if (!window.blackboxTestEnv.canReachBackend) {
                throw new ConnectionLostError();
            }
            return originalSend.apply(this, [body]);
        };
    }, "Blackbox Oracle is now enabled");
}

export function disableBlackboxOracle() {
    return run(() => {
        window.fetch = originalFetch;
    }, "Blackbox Oracle is now disabled");
}

export function checkBlackboxRequestCounter(
    count = {},
    resetCounter = true,
    checkExpectedRequestSum = true
) {
    return run(() => {
        for (const [key, value] of Object.entries(count)) {
            if (window.blackboxRequestCounter[key] !== value) {
                throw new Error(
                    `Expected ${key} to be ${value}, but got ${window.blackboxRequestCounter[key]}`
                );
            }
        }
        // Make sure the POS don't make unexpected requests
        if (checkExpectedRequestSum) {
            const expectedSum = Object.values(count).reduce((a, b) => a + b, 0);
            const actualSum = Object.values(window.blackboxRequestCounter).reduce(
                (a, b) => a + b,
                0
            );
            if (expectedSum !== actualSum) {
                throw new Error(
                    `Expected total blackbox requests to be ${expectedSum}, but got ${actualSum}. \nFull counter: ${JSON.stringify(
                        window.blackboxRequestCounter
                    )}\nExpected counts: ${JSON.stringify(count)}`
                );
            }
        }
        if (resetCounter) {
            window.blackboxRequestCounter = Object.fromEntries(
                Object.keys(window.blackboxRequestCounter).map((key) => [key, 0])
            );
        }
    }, "Check blackbox request counter");
}

export async function generateAndCheckTicket(order, expectedTicketVatLabel = "VAT TICKET") {
    const ticket = await posmodel.printer.renderer.toHtml(posmodel.orderReceiptComponent, {
        order,
        basic_receipt: false,
    });

    const text = ticket.querySelector(".blackbox-data").textContent;
    const requiredFields = [
        "fdmId:",
        "fdmDateTime:",
        "eventLabel:",
        "eventCounter:",
        "totalCounter:",
        "shortSignature:",
    ];

    for (const field of requiredFields) {
        if (!text.includes(field)) {
            throw new Error(`Missing field in blackbox data: ${field}`);
        }
    }

    const vatLabel = document.querySelector(".pos-receipt-vat").textContent;
    const expectedLabel = `${expectedTicketVatLabel}${order.pos_reference}`;
    if (!vatLabel.includes(expectedLabel)) {
        throw new Error(`Missing VAT label in receipt: '${expectedLabel}' but got '${vatLabel}'`);
    }

    const vatTable = document.querySelector(".l10n_be_vat_table");
    if (!vatTable) {
        throw new Error("Missing VAT table in receipt");
    }
}
