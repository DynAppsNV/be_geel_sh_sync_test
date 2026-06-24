import { expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { onRpc } from "@web/../tests/web_test_helpers";
const { DateTime } = luxon;
import { roundCurrency } from "@point_of_sale/app/models/utils/currency";
import { computeComboItems } from "@point_of_sale/app/models/utils/compute_combo_items";

export const expectTransactionLine = (
    transaction,
    product,
    quantity,
    quantityType,
    price,
    codeVat,
    lineType,
    negativeQuantityReason = false
) => {
    const total = price * quantity;
    expect(transaction.lineType).toBe(lineType);
    expect(transaction.mainProduct.productId).toBe(`product_id_${product.id}`);
    expect(transaction.mainProduct.productName).toBe(product.name);
    expect(transaction.mainProduct.quantity).toBe(quantity);
    expect(transaction.mainProduct.quantityType).toBe(quantityType);
    expect(transaction.mainProduct.unitPrice).toBe(price);

    if (transaction.mainProduct.vats.length) {
        expect(transaction.mainProduct.vats[0].label).toBe(codeVat);
        expect(transaction.mainProduct.vats[0].price).toBe(total);
    }

    if (negativeQuantityReason) {
        expect(transaction.mainProduct.negQuantityReason).toBe(negativeQuantityReason);
    }
};

export const expectTransactionTotals = (transaction, currency) => {
    // Compute sum of lineTotals and ensure it equals transactionTotal
    const sumLines = transaction.transactionLines.reduce((acc, line) => acc + line.lineTotal, 0);
    const roundedSumLines = roundCurrency(sumLines, currency);
    expect(transaction.transactionTotal).toBe(roundedSumLines);
    // For each transaction line, compute lineTotal (sum of vat prices + priceChanges)
    // and ensure it equals the lineTotal
    for (const transLine of transaction.transactionLines) {
        const sumVats = transLine.mainProduct.vats.length
            ? transLine.mainProduct.vats.reduce(
                  (acc, vat) =>
                      acc + vat.price + vat.priceChanges.reduce((a, pc) => a + pc.amount, 0),
                  0
              )
            : transLine.subProducts.reduce(
                  (acc, subProd) =>
                      acc +
                      subProd.vats.reduce(
                          (a, vat) =>
                              a +
                              vat.price +
                              vat.priceChanges.reduce((ac, pc) => ac + pc.amount, 0),
                          0
                      ),
                  0
              );
        const roundedSumVats = roundCurrency(sumVats, currency);
        expect(transLine.lineTotal).toBe(roundedSumVats);
    }
};

export const expectGeneralProperties = (
    input,
    {
        order = false,
        posId = "CPOS0031234567",
        bookingPeriodId = "0ca2ebb7-5f77-4d03-99a9-77b5673ab248",
        posSwVersion = "1.0",
        ticketMedium = "PAPER",
        employeeId = "1234567890",
        estNo = "8789456149",
        orderPrice = null,
        mustHavePriceChanges = false,
    } = {}
) => {
    expect(input.posId).toBe(posId);
    expect(input.bookingPeriodId).toBe(bookingPeriodId);
    expect(input.posSwVersion).toBe(posSwVersion);
    expect(input.ticketMedium).toBe(ticketMedium);
    expect(input.employeeId).toBe(employeeId);
    expect(input.estNo).toBe(estNo);
    expect(input.terminalId).not.toBeEmpty();
    expect(isRFC3339DateTime(input.posDateTime)).toBe(true);
    expect(isValidISODate(input.bookingDate)).toBe(true);

    if (input.transaction && order) {
        // Validate priceChanges per vat line when not expected
        if (!mustHavePriceChanges) {
            for (const transLine of input.transaction.transactionLines) {
                if (transLine.lineType != "COMPOSITE_PRODUCT") {
                    transLine.mainProduct.vats.forEach((vat) => {
                        const filteredPriceChanges = vat.priceChanges.filter(
                            (pc) => pc.type !== "INTERNAL"
                        );
                        expect(filteredPriceChanges).toBeEmpty();
                    });
                }
            }
        }

        // Validate COMPOSITE_PRODUCT vat structure
        for (const transLine of input.transaction.transactionLines) {
            if (transLine.lineType == "COMPOSITE_PRODUCT") {
                expect(transLine.mainProduct.vats.length).toBe(0);
                transLine.subProducts.forEach((subProd) => {
                    expect(subProd.vats.length).toBeGreaterThan(0);
                });
            }
        }

        // Validate transaction and line totals
        expectTransactionTotals(input.transaction, order.currency);

        if (input.financials?.length) {
            const sumFinancials = input.financials.reduce((acc, fin) => acc + fin.amount, 0);
            const orderPriceIncl = roundCurrency(orderPrice ?? order.priceIncl, order.currency);
            expect(orderPriceIncl).toBe(sumFinancials);
        }
    }
    if (input.fdmRef?.fdmDateTime) {
        expect(isRFC3339DateTimeUTC(input.fdmRef.fdmDateTime)).toBe(true);
    }
};

export const expectCostCenter = (costCenter, id, type, reference) => {
    expect(costCenter.id).toBe(id);
    expect(costCenter.type).toBe(type);
    expect(costCenter.reference).toBe(reference);
};

export const expectFinancial = (
    financial,
    name,
    amountType,
    amount,
    type,
    inputMethod = "MANUAL"
) => {
    expect(financial.name).toBe(name);
    expect(financial.amountType).toBe(amountType);
    expect(financial.amount).toBe(amount);
    expect(financial.type).toBe(type);
    expect(financial.inputMethod).toBe(inputMethod);
    expect(financial.id).not.toBeEmpty();
};

export const generatePosOrder = (
    models,
    rawLines = [],
    rawPayments = [],
    { orderId = 1, refundedOrderId = null } = {}
) => {
    let lineId = 1;
    let paymentId = 1;

    const lines = rawLines.map((line) => ({
        ...line,
        id: lineId++,
        order_id: orderId,
    }));

    const payments = rawPayments.map((payment) => ({
        ...payment,
        id: paymentId++,
        pos_order_id: orderId,
    }));

    const data = models.loadConnectedData({
        "pos.order": [
            {
                id: orderId,
                state: rawPayments.length ? "paid" : "draft",
                lines: lines.map((line) => line.id),
                payment_ids: payments.map((payment) => payment.id),
                refunded_order_id: refundedOrderId,
                is_refund: refundedOrderId ? true : false,
            },
        ],
        "pos.order.line": lines,
        "pos.payment": payments,
    });

    const order = data["pos.order"][0];
    return order;
};

export const getComboOrder = (store, paid = false, addSingleProductLine = false) => {
    const models = store.models;
    const menu = models["product.product"].find((m) => m.name === "Business Menu All-In");
    const starter = models["product.product"].find((m) => m.name === "Carpaccio Beef");
    const main = models["product.product"].find((m) => m.name === "Burger of the Chef");
    const wine = models["product.product"].find((m) => m.name === "Matching Wines");

    const order = store.addNewOrder();

    if (addSingleProductLine) {
        const coca = models["product.product"].find((m) => m.name === "Coca Cola");

        models["pos.order.line"].create({
            order_id: order.id,
            product_id: coca.id,
            price_unit: coca.lst_price,
            qty: 2,
        });
    }

    models["pos.order.line"].create({
        product_id: menu,
        qty: 1,
        order_id: order.id,
        price_unit: 0,
        tax_ids: menu.taxes_id,
        combo_line_ids: [
            [
                "create",
                {
                    price_unit: 16.11,
                    product_id: starter,
                    qty: 1,
                    order_id: order.id,
                    tax_ids: starter.taxes_id,
                },
            ],
            [
                "create",
                {
                    price_unit: 22.56,
                    product_id: main.id,
                    qty: 1,
                    order_id: order.id,
                    tax_ids: main.taxes_id,
                },
            ],
            [
                "create",
                {
                    price_unit: 19.330000000000002,
                    product_id: wine.id,
                    qty: 1,
                    order_id: order.id,
                    tax_ids: wine.taxes_id,
                },
            ],
        ],
    });
    if (paid) {
        payOrder(store, order);
    }
    return order;
};

export const getMultiQtyComboOrder = (store, paid = false) => {
    const models = store.models;
    // Use the dedicated "Business Menu All-In Multi Qty" product (combo_ids=[4,5,6])
    // where Multi Starters has qty_free=2, Multi Drink has qty_free=3, Single Main has qty_free=1.
    const menu = models["product.product"].find((m) => m.name === "Business Menu All-In Multi Qty");
    const starter = models["product.product"].find((m) => m.name === "Carpaccio Beef");
    const wine = models["product.product"].find((m) => m.name === "Matching Wines");
    const main = models["product.product"].find((m) => m.name === "Burger of the Chef");

    const starterItem = models["product.combo.item"].find(
        (i) => i.combo_id.name === "Multi Starters"
    );
    const wineItem = models["product.combo.item"].find((i) => i.combo_id.name === "Multi Drink");
    const mainItem = models["product.combo.item"].find((i) => i.combo_id.name === "Single Main");

    const order = store.addNewOrder();

    // Compute prices via computeComboItems.
    // Order: [starter(qty=2), wine(qty=3), main(qty=1)] — main is last with qty=1
    // to prevent the split of the last item in the algorithm.
    // originalTotal = 20*2 + 24*3 + 28*1 = 140
    // starter: round(20*58/140) = 8.29, wine: round(24*58/140) = 9.94, main: 11.6 (absorbs remainder)
    // Total: 8.29*2 + 9.94*3 + 11.6*1 = 58.0
    const childLineConf = [
        { combo_item_id: starterItem, qty: 2 },
        { combo_item_id: wineItem, qty: 3 },
        { combo_item_id: mainItem, qty: 1 },
    ];
    const comboPrices = computeComboItems(
        menu,
        childLineConf,
        order.pricelist_id,
        models["decimal.precision"].getAll(),
        models["product.template.attribute.value"].getAllBy("id"),
        [],
        order.config_id.currency_id
    );
    // comboPrices: [{starter, price_unit:8.29, qty:2}, {wine, price_unit:9.94, qty:3}, {main, price_unit:11.6, qty:1}]

    models["pos.order.line"].create({
        product_id: menu,
        qty: 1,
        order_id: order.id,
        price_unit: 0,
        tax_ids: menu.taxes_id,
        combo_line_ids: [
            [
                "create",
                {
                    price_unit: comboPrices[0].price_unit,
                    product_id: starter,
                    qty: comboPrices[0].qty,
                    order_id: order.id,
                    tax_ids: starter.taxes_id,
                },
            ],
            [
                "create",
                {
                    price_unit: comboPrices[1].price_unit,
                    product_id: wine,
                    qty: comboPrices[1].qty,
                    order_id: order.id,
                    tax_ids: wine.taxes_id,
                },
            ],
            [
                "create",
                {
                    price_unit: comboPrices[2].price_unit,
                    product_id: main,
                    qty: comboPrices[2].qty,
                    order_id: order.id,
                    tax_ids: main.taxes_id,
                },
            ],
        ],
    });
    if (paid) {
        payOrder(store, order);
    }
    return order;
};

export const payOrder = (store, order) => {
    const amountTotal = order.priceIncl;
    order.state = "paid";

    store.models["pos.payment"].create({
        amount: amountTotal,
        pos_order_id: order,
        payment_method_id: store.models["pos.payment.method"].find((m) => m.name === "Cash"),
    });
    store.addPendingOrder([order.id]);
};

export const setupPosBlackboxEnv = async (
    blackboxRpcCallback = () => void 0,
    opts = { setupCashier: true }
) => {
    onRpc("/graphql", blackboxRpcCallback);
    const id = odoo.pos_config_id;
    const deviceKey = `l10n_be_pos_blackbox-device-id-${id}`;
    localStorage.setItem(deviceKey, "deviceId");
    const store = await setupPosEnv(opts);
    return store;
};

export const waitForUnawaitedCalls = async (method, timeout = 50) =>
    new Promise((resolve) => {
        setTimeout(() => {
            method();
            resolve();
        }, timeout);
    });

export const waitForDelayedCalls = () => {
    let resolver;
    const promise = new Promise((resolve) => {
        resolver = resolve;
    });
    return { promise, resolver };
};

export const setOrderFdmSignature = (
    order,
    {
        l10n_be_fdm_id = "1234567890",
        l10n_be_fdm_date_time = "2023-10-01 12:00:00",
        eventLabel = "N",
        l10n_be_event_counter = 1,
        l10n_be_total_counter = 100,
    } = {}
) => {
    order.update({
        l10n_be_fdm_id: l10n_be_fdm_id,
        l10n_be_fdm_date_time: l10n_be_fdm_date_time,
        l10n_be_event_label: eventLabel,
        l10n_be_event_counter: l10n_be_event_counter,
        l10n_be_total_counter: l10n_be_total_counter,
    });
};

/**
 * Validates RFC3339 datetime in UTC (must end with 'Z')
 * Example: 2022-10-20T15:01:26Z
 * This format is required for FDM date time
 */
export const isRFC3339DateTimeUTC = (value) => {
    if (typeof value !== "string") {
        return false;
    }
    const rfc3339UtcRegex = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}).(\d{3})Z$/;

    const match = value.match(rfc3339UtcRegex);
    if (!match) {
        return false;
    }

    const dt = DateTime.fromISO(value, { zone: "utc" });
    return dt.isValid && dt.toUTC().toISO() === value;
};

/**
 * Validates RFC3339 datetime with timezone offset (Z is NOT allowed)
 * Example: 2022-10-20T15:01:25:512+02:00
 * This format is required for POS date time
 */
export const isRFC3339DateTime = (value) => {
    if (typeof value !== "string") {
        return false;
    }

    const rfc3339Regex =
        /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}).(\d{3})([+-]\d{2}:\d{2})$/;

    const match = value.match(rfc3339Regex);
    if (!match) {
        return false;
    }

    const dt = DateTime.fromISO(value, { setZone: true });
    return dt.isValid;
};

/**
 * Validates ISO date format YYYY-MM-DD
 */
export const isValidISODate = (value) => {
    if (typeof value !== "string") {
        return false;
    }

    const isoDateRegex = /^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;

    if (!isoDateRegex.test(value)) {
        return false;
    }

    const [year, month, day] = value.split("-").map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));

    return (
        date.getUTCFullYear() === year &&
        date.getUTCMonth() === month - 1 &&
        date.getUTCDate() === day
    );
};
