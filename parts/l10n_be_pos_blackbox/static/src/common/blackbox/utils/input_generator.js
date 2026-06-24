import { uuidv4 } from "@point_of_sale/utils";
import { roundCurrency } from "@point_of_sale/app/models/utils/currency";
import { deepEqual } from "@web/core/utils/objects";

const { DateTime } = luxon;

export class InputGenerator {
    constructor(params) {
        this.setup(params);
    }

    setup(params) {
        this.moneyName = params.moneyName || "Money In/Out";
        this.moneyAmount = params.moneyAmount || 0;
        this.order = params.order;
        this.sourceOrder = params.sourceOrder;
        this.models = params.models;
        this.inszOrBisNumber = params.inszOrBisNumber;
        this.inOutData = params.inOutData;
        this.center = params.center;
        this.discountType = params.discountType;
        this.discountScope = params.discountScope;
        this.partner = params.order?.partner_id;
        this.tipAmount = this.order?.tip_amount || 0;
        this.turnoverData = params.turnoverData;
        this.userData = params.userData;
        this.reportFdmRef = params.reportFdmRef;
        this.printerUrl = params.printerUrl;
    }

    /**
     * Returns (and lazily initialises) the persistent groupingId state stored on the order.
     * The object is mutated in-place so the counter survives across multiple signOrder calls.
     *
     * @returns {{
     *   groupingIdCount: number,
     *   globalDiscountGId: number|null,
     *   roundingAdaptationGId: number|null,
     *   lines: Record<string, {
     *     unitPriceChangeGId: number|null,
     *     menuDiscountGId:    number|null,
     *     discountGId:        number|null,
     *   }>
     * }}
     */
    _getGroupingState() {
        if (!this.order.l10n_be_grouping_id) {
            this.order.l10n_be_grouping_id = {
                groupingIdCount: 0,
                globalDiscountGId: null,
                roundingAdaptationGId: null,
                lines: {},
            };
        }
        return this.order.l10n_be_grouping_id;
    }

    /**
     * Allocates the next groupingId counter value and returns it.
     */
    _nextGroupingId() {
        const state = this._getGroupingState();
        state.groupingIdCount += 1;
        return state.groupingIdCount;
    }

    /**
     * Returns the persistent per-line record, creating it on first access.
     *
     * @param {string} lineUuid
     */
    _getLineGroupingState(lineUuid) {
        const state = this._getGroupingState();
        if (!state.lines[lineUuid]) {
            state.lines[lineUuid] = {
                unitPriceChangeGId: null,
                menuDiscountGId: null,
                discountGId: null,
            };
        }
        return state.lines[lineUuid];
    }

    /**
     * @returns {SaleInput} The sign sale input object.
     * @description
     * This function generates the input data required for signing a sale in the Blackbox FDM system.
     * It includes details such as language, VAT number, company registry number, POS ID, fiscal ticket number,
     * date and time, software version, terminal ID, booking period...
     *
     * input SaleInput {
     *   language: Language!
     *   vatNo: String!
     *   estNo: String!
     *   posId: String!
     *   posFiscalTicketNo: Int!
     *   posDateTime: String!
     *   posSwVersion: String!
     *   terminalId: String
     *   deviceId: String!
     *   bookingPeriodId: String!
     *   bookingDate: String!
     *   ticketMedium: TicketMedium!
     *   employeeId: String!
     *   fdmRef: FdmReferenceInput
     *   costCenter: CostCenterInput
     *   transaction: TransactionInput!
     *   financials: [PaymentLineInput!]!
     * }
     */
    generateSignSaleInput(empty = false) {
        let transaction = {
            transactionLines: [],
            transactionTotal: 0.0,
        };
        if (!empty) {
            transaction = this.generateTransactionInput();
        }
        const res = {
            ...this.generateCommonInput(),
            ticketMedium: this.getReceiptTicketMedium(),
            transaction,
            financials: this.generateFinancialsInput(),
            costCenter: this.order.generateCostCenterInput(),
        };

        if (this.order.refunded_order_id) {
            res.fdmRef = this.generateFdmReferenceInput(this.order.refunded_order_id);
        }
        return res;
    }

    getTicketAndDeviceNb() {
        const id = odoo.pos_config_id;
        const ticketKey = `l10n_be_pos_blackbox-fiscal-ticket-nb-${id}`;
        const deviceKey = `l10n_be_pos_blackbox-device-id-${id}`;

        let ticket = parseInt(localStorage.getItem(ticketKey));
        let device = localStorage.getItem(deviceKey);

        if (!ticket || !device) {
            [ticket, device] = [0, uuidv4()];
            localStorage.setItem(deviceKey, device);
        }
        ticket = (ticket % 999999999) + 1;
        localStorage.setItem(ticketKey, ticket);

        return [ticket, device];
    }

    /**
     * Generates common input data for Blackbox transactions.
     *
     * @param {Object} order - The POS order object.
     * @param {string} inszOrBisNumber - The employee's NISS or BIS number.
     * @returns {Object} The common input data for Blackbox transactions.
     */
    generateCommonInput() {
        const company = this.models["res.company"].getFirst();
        const config = this.models["pos.config"].getFirst();
        const session = this.models["pos.session"].getFirst();
        const now = DateTime.now();

        const [ticketNb, deviceId] = this.getTicketAndDeviceNb();

        return {
            language: "FR",
            vatNo: company.vat,
            estNo: config.establishment_number,
            posId: config.l10n_be_pos_id,
            posFiscalTicketNo: parseInt(ticketNb),
            posDateTime: now.toISO(),
            posSwVersion: odoo.info?.server_version || config._server_version.server_version,
            terminalId: config.id.toString(), // Config identifier, using the config id since we don't have
            deviceId: deviceId, // Unique by devices, the only way is to create a UUID for each opened devices
            bookingPeriodId: session.booking_period_id,
            bookingDate: (session.start_at || now).toISODate(), // Sometime start_at is not set before first clock-in
            employeeId: this.inszOrBisNumber,
        };
    }

    getReceiptTicketMedium() {
        return this.printerUrl ? "PAPER" : "DIGITAL";
    }

    /**
     * @returns {TransactionInput}
     * @description
     * Product lines, including all changes (such as price changes).
     *
     * input TransactionInput {
     *   transactionLines: [TransactionLineInput!]!
     *   transactionTotal: Float!
     * }
     */
    generateTransactionInput() {
        return {
            transactionLines: Object.values(this.generateTransactionLinesInput()).map(
                ({ transLine }) => transLine
            ),
            transactionTotal: this.getTransactionTotal(),
        };
    }

    getTransactionTotal() {
        return roundCurrency(this.order.priceIncl - this.tipAmount, this.order.currency);
    }

    /**
     * Generates a single transaction line object for a given order line.
     *
     * @param {OrderLine} line - The order line to generate a transaction line for
     * @returns {TransactionLineInput}
     */
    generateTransactionLine(
        line,
        {
            priceUnit = line.blackboxPriceUnitNoDiscount,
            discount = line.combo_line_ids?.length
                ? line.combo_line_ids[0].discount
                : line.discount,
            globalDiscount = line.order_id.globalDiscountPc,
            qty = line.qty,
        } = {}
    ) {
        const generateSubProductInput = (lines) => {
            const oldState = this.discountType;
            this.discountType = "MENU_DISCOUNT";
            const generated = lines.map((l) => {
                const priceUnit = l.blackboxPriceUnitNoDiscount;
                const subQty = line.qty !== 0 ? (l.qty / line.qty) * qty : l.qty;
                return this.generateProductInput(l, {
                    priceUnit,
                    discount,
                    globalDiscount,
                    qty: subQty,
                });
            });
            this.discountType = oldState;
            return generated;
        };

        const type = line.combo_line_ids.length ? "COMPOSITE_PRODUCT" : "SINGLE_PRODUCT";
        const productInput = this.generateProductInput(line, {
            priceUnit,
            discount,
            globalDiscount,
            qty,
        });
        const subProducts = line.combo_line_ids?.length
            ? generateSubProductInput(line.combo_line_ids)
            : [];

        return {
            lineType: type,
            mainProduct: productInput,
            lineTotal: this.getTransactionLineTotal(line, qty),
            ...(subProducts?.length && { subProducts: subProducts }),
        };
    }

    /**
     * Generates a map of transaction line inputs keyed by order line UUID.
     *
     * Each entry contains:
     *   - `transLine`: the transaction line payload sent to the blackbox
     *   - `lineInfos`: additional metadata from the original order line (price, discounts, quantity)
     *
     * The function also handles rounding adjustments to ensure:
     *   1. The sum of all `lineTotal` values matches the overall transaction total
     *   2. Each `lineTotal` matches the sum of its VAT prices + price changes
     *
     * Any remaining rounding discrepancies are distributed across lines/VATs as
     * `ROUNDING_ADAPTATION` price change entries.
     *
     * @returns {{ [uuid: string]: { transLine: TransactionLineInput, lineInfos: LineInfos } }}
     *
     * input TransactionLineInput {
     *   lineType: TransactionLineType!
     *   mainProduct: ProductInput!
     *   subProducts: [ProductInput!]
     *   costCenter: CostCenterInput
     *   lineTotal: Float!
     * }
     * TransactionLineType: SINGLE_PRODUCT; COMPOSITE_PRODUCT
     * @example
     * // Get the full map
     * const result = this.generateTransactionLinesInput();
     * // { uuid1: { transLine: {...}, lineInfos: {...} }, uuid2: ... }
     * // Extract only transLines
     * const transLines = Object.values(this.generateTransactionLinesInput()).map(({ transLine }) => transLine);
     */
    generateTransactionLinesInput() {
        const linesArray = [];
        const orderLines = this.order.linesSendableToBlackbox;

        for (const line of orderLines) {
            if (line.combo_parent_id) {
                continue;
            }

            linesArray.push({
                line,
                ...this.generateTransactionLine(line),
            });
        }

        // Rounding checks
        const getTransactionTotalDifference = () => {
            const transactionTotal = this.getTransactionTotal();
            const transactionLinesTotal = linesArray.reduce((sum, line) => sum + line.lineTotal, 0);
            return this.order.currency.round(transactionTotal - transactionLinesTotal);
        };
        const getLineTotalDifference = (line) => {
            const lineTotal = line.lineTotal;
            const calculatedLineTotal = line.mainProduct.vats.length
                ? line.mainProduct.vats.reduce((acc, vat) => acc + this.getTotalFromVat(vat), 0)
                : line.subProducts.reduce(
                      (acc, subProd) =>
                          acc + subProd.vats.reduce((a, vat) => a + this.getTotalFromVat(vat), 0),
                      0
                  );
            return this.order.currency.round(lineTotal - calculatedLineTotal);
        };
        const areAllLineTotalsCorrect = () =>
            linesArray.every((line) => getLineTotalDifference(line) === 0);

        const totalDifference = getTransactionTotalDifference();

        const buildReturnObject = () =>
            linesArray.reduce((acc, entry) => {
                const { line, ...transLine } = entry;
                acc[line.uuid] = this._buildTransactionLineWithInfo(line, transLine);
                return acc;
            }, {});

        if (totalDifference === 0 && areAllLineTotalsCorrect()) {
            return buildReturnObject();
        }

        const distributeError = (totalError, factors, apply) => {
            const nbErrors = Math.abs(totalError) * 100;
            const sign = Math.sign(totalError);
            let remaining = nbErrors;

            for (const factor of factors) {
                if (!remaining) {
                    break;
                }
                const errorToApply = Math.min(Math.round(factor.weight * nbErrors), remaining);
                remaining -= errorToApply;
                apply(factor, (sign * errorToApply) / 100);
            }
            for (let i = 0; i < remaining; i++) {
                apply(factors[i], sign * 0.01);
            }
        };

        if (totalDifference !== 0) {
            distributeError(
                totalDifference,
                this.getNormalizedLineFactors(linesArray),
                (factor, adjustment) => {
                    linesArray[factor.index].lineTotal += adjustment;
                }
            );
        }

        // Per-line rounding adaptation
        for (const line of linesArray) {
            const lineDiff = getLineTotalDifference(line);
            if (lineDiff !== 0) {
                const isCompositeLine = line.mainProduct.vats.length == 0;
                const rawFactors = this.normalizeFactors(this.getLineFactors(line));
                const factors = rawFactors.map((f) =>
                    isCompositeLine
                        ? { subIndex: f[0], vatIndex: f[1], weight: f[2] }
                        : { vatIndex: f[0], weight: f[1] }
                );

                // Allocate / reuse ONE shared groupingId for all ROUNDING_ADAPTATION entries
                const roundingGId = this._getRoundingAdaptationGId();

                distributeError(lineDiff, factors, (factor, adjustment) => {
                    let priceChange;
                    if (!isCompositeLine) {
                        priceChange = line.mainProduct.vats[factor.vatIndex].priceChanges;
                    } else {
                        priceChange =
                            line.subProducts[factor.subIndex].vats[factor.vatIndex].priceChanges;
                    }

                    if (adjustment !== 0) {
                        priceChange.push({
                            id: "6",
                            groupingId: roundingGId,
                            name: "ROUNDING_ADAPTATION",
                            scope: "LINE",
                            type: "INTERNAL",
                            amount: adjustment,
                        });
                    }
                });
            }
        }

        for (const line of linesArray) {
            line.lineTotal = this.order.currency.round(line.lineTotal);
        }

        return buildReturnObject();
    }

    /**
     * Builds the `{ transLine, lineInfos }` record for a single order line entry.
     * @returns {{ transLine: TransactionLineInput, lineInfos: LineInfos }}
     */
    _buildTransactionLineWithInfo(line, transLine) {
        return {
            transLine,
            lineInfos: {
                priceUnit: line.blackboxPriceUnitNoDiscount || 0,
                discount: line.discount || 0,
                globalDiscount: line.order_id.globalDiscountPc || 0,
                qty: line.qty || 0,
            },
        };
    }

    getTotalFromVat(vat) {
        return vat.price + vat.priceChanges.reduce((a, pc) => a + pc.amount, 0);
    }

    getLineFactors(line) {
        const labelToTax = {
            A: 0.21,
            B: 0.12,
            C: 0.06,
            D: 0.0,
            X: 0.0,
        };
        const isCompositeLine = line.mainProduct.vats.length == 0;
        return isCompositeLine
            ? line.subProducts.flatMap((subProduct, index) =>
                  subProduct.vats.map((vat, vatIndex) => [
                      index,
                      vatIndex,
                      (this.getTotalFromVat(vat) / (1 + labelToTax[vat.label])) *
                          labelToTax[vat.label],
                  ])
              )
            : line.mainProduct.vats.map((vat, vatIndex) => [
                  vatIndex,
                  (this.getTotalFromVat(vat) / (1 + labelToTax[vat.label])) * labelToTax[vat.label],
              ]);
    }

    getNormalizedLineFactors(lines) {
        const labelToTax = {
            A: 0.21,
            B: 0.12,
            C: 0.06,
            D: 0.0,
            X: 0.0,
        };
        const reduceFn = (sum, vat) => {
            const price = vat.price;
            const taxRate = labelToTax[vat.label];
            return sum + Math.abs((price / (1 + taxRate)) * taxRate);
        };
        const sumVats = (transLine) =>
            transLine.mainProduct.vats.length
                ? transLine.mainProduct.vats?.reduce(reduceFn, 0)
                : transLine.subProducts.reduce(
                      (acc, subProd) => acc + subProd.vats.reduce(reduceFn, 0),
                      0
                  );
        const rawFactors = this.normalizeFactors(
            lines.map((line, lineIndex) => [lineIndex, sumVats(line)])
        );
        return rawFactors.map((f) => ({ index: f[0], weight: f[1] }));
    }

    normalizeFactors(factors) {
        if (factors.length === 0) {
            return [];
        }
        let index = 0;
        if (factors[0].length == 2) {
            // Classic products factors
            index = 1;
        } else {
            // Composite products factors
            index = 2;
        }
        const sumFactors = factors.reduce((sum, f) => sum + f[index], 0);
        if (sumFactors === 0) {
            factors.forEach((f) => (f[index] = 0));
            return factors;
        }
        factors.forEach((f) => (f[index] = f[index] / sumFactors));
        return factors.sort((a, b) => b[index] - a[index]);
    }

    /**
     * Calculates the total for a transaction line, including global discount and logic.
     * @param {*} line
     * @returns {number}
     */
    getTransactionLineTotal(line, qty = line.qty) {
        const priceUnit = line.blackboxPriceUnit;
        const priceWithQty = priceUnit * this.getLineActualQty(line, qty);
        const globalDiscountPc = this.order.globalDiscountPc;
        const linePrice = globalDiscountPc
            ? priceWithQty * (1 - globalDiscountPc / 100)
            : priceWithQty;
        return roundCurrency(linePrice, line.order_id.currency);
    }

    /**
     * @description
     * This function generates the input; data required for a copy in the Blackbox FDM.
     * input CopyInput {
     *   language: Language!
     *   vatNo: String!
     *   estNo: String!
     *   posId: String!
     *   posFiscalTicketNo: Int!
     *   posDateTime: String!
     *   posSwVersion: String!
     *   terminalId: String
     *   deviceId: String!
     *   bookingPeriodId: String!
     *   bookingDate: String!
     *   ticketMedium: TicketMedium!
     *   employeeId: String!
     *   fdmRef: FdmReferenceInput!
     * }
     */
    generateCopyInput() {
        return {
            ...this.generateCommonInput(),
            fdmRef: this.generateFdmReferenceInput(),
            ticketMedium: this.getReceiptTicketMedium(),
        };
    }

    generateInvoiceCopyInput() {
        return {
            ...this.generateCommonInput(),
            ticketMedium: "DIGITAL",
            fdmRef: {
                fdmId: this.order.l10n_be_I_fdm_id,
                fdmDateTime: this.order.l10n_be_I_fdm_date_time.toUTC().toISO(),
                eventLabel: this.order.l10n_be_I_event_label,
                eventCounter: this.order.l10n_be_I_event_counter,
                totalCounter: this.order.l10n_be_I_total_counter,
            },
        };
    }

    generateReportCopyInput() {
        return {
            ...this.generateCommonInput(),
            fdmRef: this.reportFdmRef,
            ticketMedium: "DIGITAL",
        };
    }

    /**
     * @description
     * This function generates the input data required for an invoice in the Blackbox FDM.
     * input InvoiceInput {
     *   language: Language!
     *   vatNo: String!
     *   estNo: String!
     *   posId: String!
     *   posFiscalTicketNo: Int!
     *   posDateTime: String!
     *   posSwVersion: String!
     *   terminalId: String
     *   deviceId: String!
     *   bookingPeriodId: String!
     *   bookingDate: String!
     *   ticketMedium: TicketMedium!
     *   employeeId: String!
     *   invoiceNo: String!
     *   costCenter: costCenterInput
     *   customerVatNo: String!
     *   fdmRefs: [FdmReferenceInput!]!
     * }
     */
    generateInvoiceInput() {
        return {
            ...this.generateCommonInput(),
            ticketMedium: "DIGITAL",
            customerVatNo: this.partner?.vat || "NA",
            fdmRefs: [this.generateFdmReferenceInput()],
            invoiceNo: this.order?.account_move?.name || "NA",
            costCenter: this.order.generateCostCenterInput(),
        };
    }

    /**
     * @param {*} models
     * @param {*} inszOrBisNumber
     * @returns {DrawerOpenInput} The drawer open input object.
     *
     * @description
     * This function generates the input data required for opening a drawer in the Blackbox FDM.
     *
     * input DrawerOpenInput {
     *   language: Language!
     *   vatNo: String!
     *   estNo: String!
     *   posId: String!
     *   posFiscalTicketNo: Int!
     *   posDateTime: String!
     *   posSwVersion: String!
     *   terminalId: String
     *   deviceId: String!
     *   bookingPeriodId: String!
     *   bookingDate: String!
     *   ticketMedium: TicketMedium!
     *   employeeId: String!
     *   drawer: DrawerInput
     * }
     */
    generateDrawerOpenInput() {
        return {
            ...this.generateCommonInput(),
            ticketMedium: "NONE",
            drawer: this.generateDrawerInput(),
        };
    }

    /**
     * @returns {MoneyInOutInput} The money in/out input object.
     * @description
     * This function generates the input data required for a money in/out transaction in the Blackbox
     *
     * input MoneyInOutInput {
     *   language: Language!
     *   vatNo: String!
     *   estNo: String!
     *   posId: String!
     *   posFiscalTicketNo: Int!
     *   posDateTime: String!
     *   posSwVersion: String!
     *   terminalId: String
     *   deviceId: String!
     *   bookingPeriodId: String!
     *   bookingDate: String!
     *   ticketMedium: TicketMedium!
     *   employeeId: String!
     *   financials: [MoneyInOutLineInput!]!
     * }
     */
    generateMoneyInOutInput() {
        return {
            ...this.generateCommonInput(),
            ticketMedium: this.getReceiptTicketMedium(),
            financials: [this.generateMoneyInOutLineInput()],
        };
    }

    /**
     * @returns {MoneyInOutLineInput} The money in/out line input object.
     * @description
     * This function generates the input data for a money in/out line in the Blackbox FDM
     *
     * input MoneyInOutLineInput {
     *   id: String!
     *   name: String!
     *   type: PaymentType!
     *   provider: String
     *   inputMethod: InputMethod!
     *   amount: Float!
     *   amountType: MoneyInOutLineType!
     *   foreignCurrency: ForeignCurrencyInput
     *   reference: String
     *   drawer: DrawerInput
     * }
     */
    generateMoneyInOutLineInput() {
        return {
            id: uuidv4(),
            name: this.moneyName,
            type: "CASH",
            inputMethod: "MANUAL",
            amount: parseInt(this.moneyAmount) || 0,
            amountType: "MONEY_IN_OUT",
            drawer: this.generateDrawerInput(),
        };
    }

    /**
     * @returns {DrawerInput} The drawer input object.
     * @description
     * This function generates the input data for a drawer in the Blackbox FDM
     *
     * input DrawerInput {
     *   id: String!
     *   name: String!
     * }
     */
    generateDrawerInput() {
        return {
            id: this.printerUrl || "main_drawer",
            name: "Main Drawer",
        };
    }

    /**
     * @returns {PreBillInput} The pre-bill input object.
     * @description
     * This function generates the input data required for a pre-bill in the Blackbox FDM
     *
     * input PreBillInput {
     *   language: Language!
     *   vatNo: String!
     *   estNo: String!
     *   posId: String!
     *   posFiscalTicketNo: Int!
     *   posDateTime: String!
     *   posSwVersion: String!
     *   terminalId: String
     *   deviceId: String!
     *   bookingPeriodId: String!
     *   bookingDate: String!
     *   ticketMedium: TicketMedium!
     *   employeeId: String!
     *   costCenter: CostCenterInput
     *   transaction: TransactionInput!
     * }
     */
    generatePreBillInput() {
        return {
            ...this.generateCommonInput(),
            ticketMedium: this.getReceiptTicketMedium(),
            transaction: this.generateTransactionInput(),
            costCenter: this.order.generateCostCenterInput(),
        };
    }

    /**
     * @returns {CostCenterChangeInput} The cost center change input object.
     * @description
     * This function generates the input data required for changing the cost center in the Blackbox FDM
     *
     * input CostCenterChangeInput {
     *   language: Language!
     *   vatNo: String!
     *   estNo: String!
     *   posId: String!
     *   posFiscalTicketNo: Int!
     *   posDateTime: String!
     *   posSwVersion: String!
     *   terminalId: String
     *   deviceId: String!
     *   bookingPeriodId: String!
     *   bookingDate: String!
     *   ticketMedium: TicketMedium!
     *   employeeId: String!
     *   transfer: TransferInput!
     * }
     */
    generateSignOrderChangeInput() {
        return {
            ...this.generateCommonInput(),
            ticketMedium: "NONE",
            transfer: this.generateTransferOrderInput(),
        };
    }

    generateSignCostCenterChangeInput(oldCostCenter, newCostCenter) {
        return {
            ...this.generateCommonInput(),
            ticketMedium: "NONE",
            transfer: this.generateTransferCostCenterInput(oldCostCenter, newCostCenter),
        };
    }

    /**
     * @returns {TransferInput} The transfer input object.
     * @description
     * This function generates the input data required for a transfer in the Blackbox FDM.
     *
     * input TransferInput {
     *   from: TransferItemInput!
     *   to: TransferItemInput!
     * }
     */
    generateTransferOrderInput() {
        const transactionLines = Object.values(this.generateTransactionLinesInput()).map(
            ({ transLine }) => transLine
        );
        const negateTransactionLines = transactionLines.map((line) =>
            this.negateTransactionLine(line, "COST_CENTER_CHANGE")
        );
        const transactionTotal = roundCurrency(
            transactionLines.reduce((sum, line) => sum + line.lineTotal, 0),
            this.order.currency
        );

        return {
            from: {
                costCenter: this.sourceOrder.generateCostCenterInput(),
                transaction: {
                    transactionLines: negateTransactionLines,
                    transactionTotal: -transactionTotal,
                },
            },
            to: {
                costCenter: this.order.generateCostCenterInput(),
                transaction: {
                    transactionLines: transactionLines,
                    transactionTotal: transactionTotal,
                },
            },
        };
    }

    generateTransferCostCenterInput(oldCostCenter, newCostCenter) {
        const transactionLines = Object.values(this.generateTransactionLinesInput()).map(
            ({ transLine }) => transLine
        );
        const negateTransactionLines = transactionLines.map((line) =>
            this.negateTransactionLine(line, "COST_CENTER_CHANGE")
        );
        const transactionTotal = roundCurrency(
            transactionLines.reduce((sum, line) => sum + line.lineTotal, 0),
            this.order.currency
        );
        return {
            from: {
                costCenter: oldCostCenter,
                transaction: {
                    transactionLines: negateTransactionLines,
                    transactionTotal: -transactionTotal,
                },
            },
            to: {
                costCenter: newCostCenter,
                transaction: {
                    transactionLines: transactionLines,
                    transactionTotal: transactionTotal,
                },
            },
        };
    }

    /**
     * @returns {TransferItemInput} The transfer item input object.
     * @description
     * This function generates the input data required for a transfer item in the Blackbox FDM.
     *
     * input TransferItemInput {
     *   costCenter: CostCenterInput!
     *   transaction: TransactionInput!
     * }
     */
    generateTransferItemInput() {
        return {
            costCenter: this.order.generateCostCenterInput(),
            transaction: this.generateTransactionInput(),
        };
    }

    /**
     * @returns {WorkInOutInput} The work in/out input object.
     * @description
     * This function generates the input data required for work in/out transactions in the Blackbox FDM.
     *
     * input WorkInOutInput {
     *   language: Language!
     *   vatNo: String!
     *   estNo: String!
     *   posId: String!
     *   posFiscalTicketNo: Int!
     *   posDateTime: String!
     *   posSwVersion: String!
     *   terminalId: String
     *   deviceId: String!
     *   bookingPeriodId: String!
     *   bookingDate: String!
     *   ticketMedium: TicketMedium!
     *   employeeId: String!
     * }
     */
    generateWorkInOutInput() {
        return {
            ...this.generateCommonInput(),
            ticketMedium: "NONE",
        };
    }

    isLineWithoutTaxes(line) {
        return !line.product_id.taxes_id || line.product_id.taxes_id.length === 0;
    }

    /**
     * Generates a VAT input object for a single product line.
     * If price is provided, it should be already rounded and will be used instead of the line's catalog price.
     */
    generateTaxVatInput(
        line,
        taxLabel,
        price = null,
        { priceUnit, discount, globalDiscount, qty }
    ) {
        // Calculate line initial price (before any price changes)
        const lineInitPrice =
            price || roundCurrency(line.blackboxProductProductPrice * qty, this.order.currency);
        return {
            label: taxLabel,
            price: lineInitPrice,
            priceChanges: this.generatePriceChangeInput(line, lineInitPrice, {
                priceUnit,
                discount,
                globalDiscount,
                qty,
            }),
        };
    }

    /**
     * @param {*} line
     * @returns {Array<VatInput>}
     * @description
     * This function generates an array of VAT input objects for a single product line.
     *
     * input VatInput {
     *   label: VatLabel!
     *   price: Float!
     *   priceChanges: [PriceChangeInput!]
     * }
     */
    generateLineVatInput(line, { priceUnit, discount, globalDiscount, qty }) {
        const getVatLabel = (taxe) => {
            switch (taxe.amount) {
                case 21:
                    return "A";
                case 12:
                    return "B";
                case 6:
                    return "C";
                case 0:
                    return "D";
                default:
                    return "X";
            }
        };
        // We don't want to have vats input for combo parent lines
        if (line.combo_line_ids.length) {
            return [];
        }

        // Lines without taxes or tip lines are labeled with "X" vat
        return this.isLineWithoutTaxes(line) || line.isTipLine()
            ? [
                  this.generateTaxVatInput(line, "X", null, {
                      priceUnit,
                      discount,
                      globalDiscount,
                      qty,
                  }),
              ]
            : line.product_id.taxes_id.map((vat) =>
                  this.generateTaxVatInput(line, getVatLabel(vat), null, {
                      priceUnit,
                      discount,
                      globalDiscount,
                      qty,
                  })
              );
    }

    getQuantityType(line) {
        const productUom = line.product_id.product_tmpl_id.uom_id;
        switch (productUom.name.toLowerCase()) {
            case "kg":
                return "KILOGRAM";
            case "m":
                return "METER";
            case "l":
                return "LITER";
            case "hours":
                return "HOUR";
            default:
                return "PIECE";
        }
    }

    /**
     * @param {*} line
     * @returns {ProductInput}
     * @description
     * This function generates a product input object for a single product line.
     *
     * input ProductInput {
     *   gtin: String
     *   productId: String!
     *   productName: String!
     *   departmentId: String!
     *   departmentName: String!
     *   quantity: Float!
     *   quantityType: QuantityType!
     *   negQuantityReason: NegQuantityReason
     *   unitPrice: Float!
     *   vats: [VatInput!]!
     * }
     */
    generateProductInput(line, { priceUnit, discount, globalDiscount, qty }) {
        const negQuantityReason = qty < 0 ? { negQuantityReason: "REFUND" } : {};
        const productCategory = line.product_id.product_tmpl_id?.pos_categ_ids[0];
        const lineVats = this.generateLineVatInput(line, {
            priceUnit,
            discount,
            globalDiscount,
            qty,
        });
        line.l10n_be_vats = lineVats;
        return {
            ...negQuantityReason,
            productId: `product_id_${line.product_id.id}`,
            productName: line.product_id.display_name,
            departmentId: productCategory ? productCategory.id.toString() : "0",
            departmentName: productCategory ? productCategory.name : "Not Categorized",
            quantity: qty,
            quantityType: this.getQuantityType(line),
            unitPrice: line.blackboxProductProductPrice,
            vats: lineVats,
        };
    }

    /**
     * @returns {FdmReferenceInput}
     * @description
     * This array contains the references assigned by the FDM to previous events to which it refers.
     *
     * input FdmReferenceInput {
     *   fdmId: String!
     *   fdmDateTime: String!
     *   eventLabel: EventLabel!
     *   eventCounter: Int!
     *   totalCounter: Int!
     * }
     */
    generateFdmReferenceInput(order = this.order) {
        return {
            fdmId: order.l10n_be_fdm_id,
            fdmDateTime: order.l10n_be_fdm_date_time.toUTC().toISO(),
            eventLabel: order.l10n_be_event_label,
            eventCounter: order.l10n_be_event_counter,
            totalCounter: order.l10n_be_total_counter,
        };
    }

    /**
     * Returns the shared groupingId for GLOBAL_DISCOUNT (same across all lines in the
     * transaction). Allocates a new id on first call, reuses it afterwards.
     */
    _getGlobalDiscountGId() {
        const state = this._getGroupingState();
        if (state.globalDiscountGId === null) {
            state.globalDiscountGId = this._nextGroupingId();
        }
        return state.globalDiscountGId;
    }

    /**
     * Returns the shared groupingId for ROUNDING_ADAPTATION entries.
     * Allocates a new id on first call within this generation pass, reuses it afterwards.
     */
    _getRoundingAdaptationGId() {
        const state = this._getGroupingState();
        if (state.roundingAdaptationGId === null) {
            state.roundingAdaptationGId = this._nextGroupingId();
        }
        return state.roundingAdaptationGId;
    }

    /**
     * Returns the shared groupingId for a MENU_DISCOUNT (INTERNAL) entry.
     * Each distinct combo parent gets its own id; lines sharing the same parent
     * share the same id.
     *
     * @param {string} comboParentUuid
     */
    _getMenuDiscountGId(comboParentUuid) {
        const state = this._getLineGroupingState(comboParentUuid);
        if (state.menuDiscountGId === null) {
            state.menuDiscountGId = this._nextGroupingId();
        }
        return state.menuDiscountGId;
    }

    /**
     * Returns the groupingId for a UNIT_PRICE_CHANGE on a specific line.
     * Allocated once per line; reused if the same line is re-processed.
     *
     * @param {string} lineUuid
     */
    _getUnitPriceChangeGId(lineUuid) {
        const state = this._getLineGroupingState(lineUuid);
        if (state.unitPriceChangeGId === null) {
            state.unitPriceChangeGId = this._nextGroupingId();
        }
        return state.unitPriceChangeGId;
    }

    /**
     * Returns the groupingId for a LINE_DISCOUNT on a specific line.
     * Allocated once per line; reused if the same line is re-processed.
     *
     * @param {string} lineUuid
     */
    _getDiscountGId(lineUuid) {
        const state = this._getLineGroupingState(lineUuid);
        if (state.discountGId === null) {
            state.discountGId = this._nextGroupingId();
        }
        return state.discountGId;
    }

    // Override in 'l10n_be_pos_blackbox_loyalty'
    getLineActualQty(line, qty) {
        return qty;
    }

    /**
     * @param {*} line
     * @param {string} [discountType] - The type of discount to apply (e.g., "MenuDiscount").
     * @returns {Array<PriceChangeInput>}
     *
     * @description
     * This array is only used if price changes have been applied to this part of the item's sale price
     * during this event. This array may contain several objects if multiple price changes apply. A
     * maximum of 99 objects is allowed. The priceChange object is described in priceChange.
     *
     * input PriceChangeInput {
     *   groupingId: Int
     *   id: String!
     *   name: String!
     *   scope: PriceChangeScope!
     *   type: PriceChangeType!
     *   amount: Float!
     * }
     *
     * PriceChangeScope: LINE, EVENT
     * PriceChangeType: PUBLIC, INTERNAL
     */
    generatePriceChangeInput(line, initPrice, { priceUnit, discount, globalDiscount, qty }) {
        const res = [];
        const currency = line.order_id.currency;
        const linePrice = currency.round(line.blackboxPrice);
        const hasPriceChange = () =>
            !currency.isZero(linePrice - initPrice) ||
            line.combo_parent_id ||
            this.order.discountLines.length > 0 ||
            !currency.isZero(line.blackboxPriceUnit - priceUnit);

        if (!hasPriceChange()) {
            return res;
        }

        const sign = line.order_id.isRefund ? -1 : 1;
        const originalUPrice = line.blackboxProductProductPrice * sign;

        const lineDiscountType = this.discountType || "UNIT_PRICE_CHANGE";
        const isMenuDiscount = lineDiscountType === "MENU_DISCOUNT";

        // Sub-lines of a combo share the parent's discount groupingId
        const priceChangeLineUuid = line.combo_parent_id ? line.combo_parent_id.uuid : line.uuid;
        const actualQty = this.getLineActualQty(line, qty);

        // Compute unit-price-change values upfront (needed for both MENU_DISCOUNT and UNIT_PRICE_CHANGE)
        let unitPriceChangeEntry = null;
        if (originalUPrice !== priceUnit) {
            const isDiscount = currency.comp(originalUPrice, priceUnit) > 0;
            const amount = isDiscount
                ? -(originalUPrice - priceUnit) * actualQty
                : (priceUnit - originalUPrice) * actualQty;
            const gId = isMenuDiscount
                ? this._getMenuDiscountGId(priceChangeLineUuid)
                : this._getUnitPriceChangeGId(priceChangeLineUuid);

            unitPriceChangeEntry = {
                id: isMenuDiscount ? "1" : "3",
                groupingId: gId,
                name: lineDiscountType,
                scope: "LINE",
                type: isMenuDiscount ? "INTERNAL" : "PUBLIC",
                amount: roundCurrency(amount * sign, currency),
            };
        }

        // 1. Menu discount (INTERNAL)
        if (isMenuDiscount && unitPriceChangeEntry) {
            res.push(unitPriceChangeEntry);
        }

        // 2. Global discount
        let discountedUnitAmount = 0;
        if (discount) {
            // Compute line discount amount here so it can be used in the global discount below,
            // but the entry itself is pushed later (after global discount).
            discountedUnitAmount = (priceUnit * discount) / 100;
        }
        if (globalDiscount) {
            const gdAmount =
                (((priceUnit - discountedUnitAmount) * globalDiscount) / 100) * actualQty;
            if (gdAmount) {
                res.push({
                    id: `2_${globalDiscount}P`,
                    groupingId: this._getGlobalDiscountGId(),
                    name: `GLOBAL_DISCOUNT_${globalDiscount}P`,
                    scope: "EVENT",
                    type: "PUBLIC",
                    amount: -roundCurrency(gdAmount * sign, currency),
                });
            }
        }

        // 3. Unit price change (PUBLIC, non-menu)
        if (!isMenuDiscount && unitPriceChangeEntry) {
            res.push(unitPriceChangeEntry);
        }

        // 4. Line discount
        if (discount) {
            const lineDiscountAmount = -roundCurrency(
                discountedUnitAmount * actualQty * sign,
                currency
            );
            if (lineDiscountAmount) {
                res.push({
                    id: `4_${discount}P`,
                    groupingId: this._getDiscountGId(priceChangeLineUuid),
                    name: `DISCOUNT_${discount}P`,
                    scope: "LINE",
                    type: "PUBLIC",
                    amount: lineDiscountAmount,
                });
            }
        }

        // 5. Menu rounding adaptation (last sub-line of a combo)
        if (line.combo_parent_id && line.combo_parent_id.combo_line_ids.at(-1).uuid === line.uuid) {
            const relatedLines = line.combo_parent_id.combo_line_ids;
            const roundingAdaptation =
                currency.round(line.combo_parent_id.blackboxPrice) -
                relatedLines.reduce((sum, l) => sum + currency.round(l.blackboxPrice), 0);

            if (!currency.isZero(roundingAdaptation)) {
                res.push({
                    id: "5",
                    groupingId: this._nextGroupingId(),
                    name: "MENU_ROUNDING_ADAPTATION",
                    scope: "LINE",
                    type: "INTERNAL",
                    amount: roundCurrency(roundingAdaptation * sign, currency),
                });
            }
        }

        return res;
    }

    getMappedPaymentLineType(payment) {
        if (payment.payment_method_id.type === "cash") {
            return "CASH";
        } else if (payment.payment_method_id.type === "bank") {
            return "CARD_UNKNOWN";
        } else if (payment.payment_method_id.type === "online") {
            return "ONLINE";
        } else if (payment.payment_method_id.type === "pay_later") {
            return "CUSTOMER_CREDIT";
        } else {
            return "OTHER";
        }
    }

    generatePaymentLineInput(payment) {
        return {
            id: payment.uuid,
            name: payment.payment_method_id?.name || "UNKNOWN",
            type: this.getMappedPaymentLineType(payment),
            inputMethod: "MANUAL",
            amount: roundCurrency(payment.amount - this.tipAmount, this.order.currency),
            amountType: "PAYMENT",
            reference: payment.id.toString(),
        };
    }

    /**
     * @returns {Array<PaymentLineInput>}
     * @description
     * This function generates an array of payment line input objects for the order.
     *
     * input PaymentLineInput {
     *   id: String!
     *   name: String!
     *   type: PaymentType!
     *   provider: String
     *   inputMethod: InputMethod!
     *   amount: Float!
     *   amountType: PaymentLineType!
     *   foreignCurrency: ForeignCurrencyInput
     *   reference: String
     *   drawer: DrawerInput
     * }
     */
    generateFinancialsInput() {
        const paymentLines = this.order.payment_ids
            .map((payment) => this.generatePaymentLineInput(payment))
            .filter((line) => line);
        if (this.tipAmount) {
            const tipLine = this.order.lines.find((l) => l.isTipLine());
            paymentLines.push({
                id: tipLine?.uuid || uuidv4(),
                name: "Tip",
                type: paymentLines[0]?.type || "CASH",
                inputMethod: "MANUAL",
                amount: roundCurrency(this.tipAmount, this.order.currency),
                amountType: "TIP",
            });
        }
        if (this.order.appliedRounding) {
            const cashPayment = paymentLines.find((pl) => pl.type === "CASH");
            if (cashPayment) {
                cashPayment.amount = roundCurrency(
                    cashPayment.amount - this.order.appliedRounding,
                    this.order.currency
                );
            }
            paymentLines.push({
                id: uuidv4(),
                name: "Rounding",
                type: "CASH",
                inputMethod: "MANUAL",
                amount: roundCurrency(this.order.appliedRounding, this.order.currency),
                amountType: "ROUNDING",
            });
        }
        if (this.order.currency.isNegative(this.order.change)) {
            paymentLines.push({
                id: uuidv4(),
                name: "Change",
                type: "CASH",
                inputMethod: "MANUAL",
                amount: roundCurrency(this.order.change, this.order.currency),
                amountType: "PAYMENT",
            });
        }
        return paymentLines;
    }

    negateTransactionLine(line, negQuantityReason) {
        //Need to deepCopy the object, since we update it (and don't want to change original object 'order.l10n_be_last_transaction_by_line')
        const lineCopy = JSON.parse(JSON.stringify(line));
        lineCopy.mainProduct.quantity = -line.mainProduct.quantity;
        if (lineCopy.mainProduct.quantity < 0) {
            lineCopy.mainProduct.negQuantityReason = negQuantityReason;
        }

        lineCopy.lineTotal = -line.lineTotal;
        if (lineCopy.lineType === "SINGLE_PRODUCT") {
            lineCopy.mainProduct.vats.forEach((vat) => {
                vat.price = -vat.price;
                vat.priceChanges.forEach((pc) => {
                    pc.amount = -pc.amount;
                });
            });
        } else if (lineCopy.lineType === "COMPOSITE_PRODUCT") {
            lineCopy.subProducts.forEach((subProduct) => {
                subProduct.quantity = -subProduct.quantity;
                if (subProduct.quantity < 0) {
                    subProduct.negQuantityReason = negQuantityReason;
                }
                subProduct.vats.forEach((vat) => {
                    vat.price = -vat.price;
                    vat.priceChanges.forEach((pc) => {
                        pc.amount = -pc.amount;
                    });
                });
            });
        }
        return lineCopy;
    }

    /**
     * Builds the final payload for sign order requests.
     *
     * @param {Array<Object>} transactionLines
     * @returns {OrderInput}
     * input OrderInput {
     *   language: Language!
     *   vatNo: String!
     *   estNo: String!
     *   posId: String!
     *   posFiscalTicketNo: Int!
     *   posDateTime: String!
     *   posSwVersion: String!
     *   terminalId: String
     *   deviceId: String!
     *   bookingPeriodId: String!
     *   bookingDate: String!
     *   ticketMedium: TicketMedium!
     *   employeeId: String!
     *   costCenter: CostCenterInput!
     *   transaction: TransactionInput!
     * }
     */
    buildSignOrderPayload(transactionLines) {
        const transactionTotal = roundCurrency(
            transactionLines.reduce((sum, line) => sum + line.lineTotal, 0),
            this.order.currency
        );

        return {
            ...this.generateCommonInput(),
            ticketMedium: "NONE",
            costCenter: this.order.generateCostCenterInput(),
            transaction: {
                transactionLines,
                transactionTotal,
            },
        };
    }

    /**
     * Compute the total amount of a transaction line (VAT price + price changes) based on product type (main or subProducts)
     *
     * @param {Object} transLine - The transaction line to compute the total for
     * @returns {number} The rounded total in the order's currency
     */
    computeTransactionLineTotal(transLine) {
        const { mainProduct, subProducts } = transLine;

        const vatTotal = (vat) => {
            const priceChangesTotal = vat.priceChanges.reduce((sum, pc) => sum + pc.amount, 0);
            return vat.price + priceChangesTotal;
        };

        const vatsTotal = (vats) => vats.reduce((sum, vat) => sum + vatTotal(vat), 0);

        const sumVats = mainProduct.vats.length
            ? vatsTotal(mainProduct.vats)
            : subProducts.reduce((sum, subProd) => sum + vatsTotal(subProd.vats), 0);

        return roundCurrency(sumVats, this.order.currency);
    }

    /**
     * Generates the payload required for signing an order (non-financial).
     *
     * Compared to the last signed state, this method computes the delta of
     * transaction lines:
     *  - 1. NEW LINE: If the line was not in the last 'signOrder', we need to send it
     *  - 2. MODIFIED LINE: If the line was in the last 'signOrder' but has changed, we need to send a correction (negative line) followed by the updated line.
     *  - 3. DELETED LINE: If the line was in the last 'signOrder' but is not in the new one, we need to send a correction (negative line).
     *
     * The resulting transaction only contains the necessary changes
     * relative to the previously signed version.
     *
     * @returns {OrderInput} The sign order input object containing only delta lines.
     */
    generateSignOrderInput(initialValues = {}) {
        const transactionLinesMap = this.generateTransactionLinesInput();
        const transactionLinesToSend = [];
        const lastTransactionLinesMap = this.order.l10n_be_last_transaction_by_line || {};

        for (const [lineUuid, transactionLine] of Object.entries(transactionLinesMap)) {
            // 1. NEW LINE: If the line was not in the last 'signOrder', we need to send it
            if (!(lineUuid in lastTransactionLinesMap)) {
                if (initialValues[lineUuid]) {
                    const line = this.models["pos.order.line"].getBy("uuid", lineUuid);
                    if (!line) {
                        continue;
                    }
                    const initInfos = initialValues[lineUuid];
                    const initTransLine = this.generateTransactionLine(line, initInfos);
                    initTransLine.lineTotal = this.computeTransactionLineTotal(initTransLine);
                    transactionLinesToSend.push(initTransLine);
                    transactionLinesToSend.push(
                        ...this.generateCorrectionLines(line, initInfos, transactionLine, {
                            preserveGroupingIds: true,
                        })
                    );
                } else {
                    transactionLinesToSend.push(transactionLine.transLine);
                }
            } else {
                const lastTransLine = lastTransactionLinesMap[lineUuid];
                const line = this.models["pos.order.line"].getBy("uuid", lineUuid);
                if (!line) {
                    continue;
                }

                // 2. MODIFIED LINE: If the line was in the last 'signOrder' but has changed, we need to send update to the blackbox
                if (!deepEqual(transactionLine.transLine, lastTransLine.transLine)) {
                    transactionLinesToSend.push(
                        ...this.generateCorrectionLines(
                            line,
                            lastTransLine.lineInfos,
                            transactionLine
                        )
                    );
                }
            }
        }

        for (const [lineUuid, transactionLine] of Object.entries(lastTransactionLinesMap)) {
            // 3. DELETED LINE:
            // - If the line was in the last 'signOrder' but is not in the new one, we need to send a correction with negative quantity
            // - We also check that quantity is not 0 to avoid sending a correction for a line that was already corrected
            if (!(lineUuid in transactionLinesMap) && transactionLine.lineInfos.qty != 0) {
                transactionLinesToSend.push(
                    this.negateTransactionLine(transactionLine.transLine, "CORRECTION")
                );
            }
        }

        for (const lineUuid in initialValues) {
            // 4. ADDED LINE THEN DELETED IN DIRECT SALE:
            // - If the line was in initialValues and is not in the transactionLinesMap nor in lastTransactionLinesMap,
            // it means that the line was added and then deleted before being synced.
            // In this case, we need to send a correction for the initial line with negative quantity
            // to remove it from the blackbox.
            if (!(lineUuid in transactionLinesMap) && !(lineUuid in lastTransactionLinesMap)) {
                transactionLinesToSend.push(initialValues[lineUuid].initialTransLine);
                transactionLinesToSend.push(
                    this.negateTransactionLine(
                        initialValues[lineUuid].initialTransLine,
                        "CORRECTION"
                    )
                );
            }
        }
        this.order.uiState.transactionLinesMap = transactionLinesMap;
        return this.buildSignOrderPayload(transactionLinesToSend);
    }
    generateCorrectionLines(
        line,
        fromInfos,
        toTransactionLine,
        { preserveGroupingIds = false } = {}
    ) {
        const transactionLinesToSend = [];
        const deltaQuantity = toTransactionLine.lineInfos.qty - fromInfos.qty;
        if (deltaQuantity) {
            // If we have a delta quantity
            // Increasing quantity -> send new line for the delta quantity
            // Decreasing quantity -> send correction for the delta quantity
            let qtyAdjustmentLine = this.generateTransactionLine(line, {
                priceUnit: fromInfos.priceUnit,
                discount: fromInfos.discount,
                globalDiscount: fromInfos.globalDiscount,
                qty: Math.abs(deltaQuantity),
            });
            if (deltaQuantity < 0) {
                qtyAdjustmentLine = this.negateTransactionLine(qtyAdjustmentLine, "CORRECTION");
            }
            qtyAdjustmentLine.lineTotal = this.computeTransactionLineTotal(qtyAdjustmentLine);
            transactionLinesToSend.push(qtyAdjustmentLine);
        }

        // At this point, we know that we've sent the corrected quantity of lines, we need to check if there is a price change that needs to be send to the blackbox
        const infos = toTransactionLine.lineInfos;
        if (
            !line.order_id.currency.isZero(fromInfos.priceUnit - infos.priceUnit) ||
            (fromInfos.discount || 0) !== infos.discount ||
            fromInfos.globalDiscount !== infos.globalDiscount
        ) {
            const correctionPriceChangedLine = this.negateTransactionLine(
                this.generateTransactionLine(line, {
                    priceUnit: fromInfos.priceUnit,
                    discount: fromInfos.discount || 0,
                    globalDiscount: fromInfos.globalDiscount,
                    qty: line.qty,
                }),
                "PRICE_CHANGE"
            );
            correctionPriceChangedLine.lineTotal = this.computeTransactionLineTotal(
                correctionPriceChangedLine
            );
            transactionLinesToSend.push(correctionPriceChangedLine);

            // 2. Deep-copy the already-computed transLine (correct prices + rounding
            //    adaptations included). For lines already signed before, changed
            //    discount fields get fresh groupingIds. For initial unsynced lines,
            //    keep the already-assigned ids to avoid artificial gaps.
            const newLine = JSON.parse(JSON.stringify(toTransactionLine.transLine));
            if (!preserveGroupingIds) {
                // Refresh grouping ids only when an old id existed and must be replaced.
                // If a field appears for the first time (e.g. discount 0 -> 5),
                // toTransactionLine already contains the first valid id and we must keep it.
                const sign = line.order_id.isRefund ? -1 : 1;
                const originalUPrice = line.blackboxProductProductPrice * sign;
                const shouldRefreshUnitPriceChangeId =
                    fromInfos.priceUnit !== infos.priceUnit &&
                    fromInfos.priceUnit !== originalUPrice;
                const shouldRefreshDiscountId =
                    (fromInfos.discount || 0) !== infos.discount &&
                    Boolean(fromInfos.discount || 0);

                const discountOwnerUuid = line.combo_parent_id
                    ? line.combo_parent_id.uuid
                    : line.uuid;
                const groupingState = this._getLineGroupingState(discountOwnerUuid);
                if (shouldRefreshUnitPriceChangeId) {
                    groupingState.unitPriceChangeGId = null;
                    groupingState.menuDiscountGId = null;
                }
                if (shouldRefreshDiscountId) {
                    groupingState.discountGId = null;
                }

                const allPriceChanges =
                    newLine.lineType === "COMPOSITE_PRODUCT"
                        ? newLine.subProducts.flatMap((sp) =>
                              sp.vats.flatMap((v) => v.priceChanges)
                          )
                        : newLine.mainProduct.vats.flatMap((v) => v.priceChanges);

                if (shouldRefreshUnitPriceChangeId) {
                    const newUpcGId = this._getUnitPriceChangeGId(discountOwnerUuid);
                    const newMenuGId = this._getMenuDiscountGId(discountOwnerUuid);
                    for (const pc of allPriceChanges) {
                        if (pc.name === "UNIT_PRICE_CHANGE") {
                            pc.groupingId = newUpcGId;
                        } else if (pc.name === "MENU_DISCOUNT") {
                            pc.groupingId = newMenuGId;
                        }
                    }
                }
                if (shouldRefreshDiscountId) {
                    const newDiscGId = this._getDiscountGId(discountOwnerUuid);
                    for (const pc of allPriceChanges) {
                        if (pc.name.startsWith("DISCOUNT_")) {
                            pc.groupingId = newDiscGId;
                        }
                    }
                }
            }
            transactionLinesToSend.push(newLine);
        }
        return transactionLinesToSend;
    }
    /**
     * Generates the payload for signing a canceled order.
     *
     * This method creates correction transaction lines (negative quantities)
     * for all lines that were previously signed. It is used when an already
     * signed order must be fully canceled.
     *
     * @returns {OrderInput}
     */
    generateSignCanceledOrderInput() {
        const lastTransactionLinesMap = this.order.l10n_be_last_transaction_by_line || {};
        const transactionLinesToSend = Object.values(lastTransactionLinesMap)
            .filter(({ lineInfos }) => lineInfos.qty !== 0)
            .map(({ transLine }) => transLine)
            .map((line) => this.negateTransactionLine(line, "CORRECTION"));
        return this.buildSignOrderPayload(transactionLinesToSend);
    }

    /**
     * This is called after transferring an order to a different table and when we need to apply the global discount on all lines.
     * @param {Object} transLines - Map of line UUID to { transLine, lineInfos } entries representing the last signed state.
     * @param {Object|null} sourceLinesNextUuidMap - Optional map from old UUID to new UUID (for merged/split lines).
     * @param {number} [targetGlobalDiscount] - The global discount percentage to apply to the corrected (POS) lines.
     *   Defaults to the order's current global discount. Pass 0 when the target order has no GD (e.g. split transfer).
     */
    generateSignGlobalDiscountChangeInput(
        transLines,
        sourceLinesNextUuidMap,
        targetGlobalDiscount = this.order.globalDiscountPc
    ) {
        const transactionLinesToSend = [];

        for (const [uuid, { transLine, lineInfos }] of Object.entries(transLines)) {
            // Negate directly the existing transLine
            const negatedLine = this.negateTransactionLine(transLine, "PRICE_CHANGE");
            negatedLine.lineTotal = this.computeTransactionLineTotal(negatedLine);
            transactionLinesToSend.push(negatedLine);

            const lineUuid = sourceLinesNextUuidMap ? sourceLinesNextUuidMap[uuid] : uuid;
            const line = this.models["pos.order.line"].getBy("uuid", lineUuid);
            if (line) {
                // Add the line with the new global discount, using the new uuid from sourceLinesNextUuidMap
                const newLine = this.generateTransactionLine(line, {
                    priceUnit: lineInfos.priceUnit,
                    discount: lineInfos.discount,
                    globalDiscount: targetGlobalDiscount,
                    qty: lineInfos.qty,
                });
                newLine.lineTotal = this.computeTransactionLineTotal(newLine);
                transactionLinesToSend.push(newLine);
            }
        }
        return this.buildSignOrderPayload(transactionLinesToSend);
    }

    /**
     * @returns {ReportTurnoverXInput} The turnover X report input object.
     * @description
     * This function generates the input data required for the Turnover X report in the Blackbox FDM.
     *
     * input ReportTurnoverXInput {
     *   language: Language!
     *   vatNo: String!
     *   estNo: String!
     *   posId: String!
     *   posFiscalTicketNo: Int!
     *   posDateTime: String!
     *   posSwVersion: String!
     *   terminalId: String
     *   deviceId: String!
     *   bookingPeriodId: String!
     *   bookingDate: String!
     *   ticketMedium: TicketMedium!
     *   employeeId: String!
     *   posDevices: [PosDeviceInput!]!
     *   fdmDevices: [FdmDeviceInput!]!
     *   turnover: TurnoverInput!
     * }
     */
    generateTurnoverXInput() {
        return {
            ...this.generateCommonInput(),
            ticketMedium: "DIGITAL",
            posDevices: this.turnoverData.posDevices,
            fdmDevices: this.turnoverData.fdmDevices,
            turnover: this.generateTurnoverInput(),
        };
    }

    /**
     * @returns {ReportTurnoverZInput} The turnover Z report input object.
     * @description
     * This function generates the input data required for the Turnover Z report in the Blackbox FDM.
     *
     * input ReportTurnoverZInput {
     *   language: Language!
     *   vatNo: String!
     *   estNo: String!
     *   posId: String!
     *   posFiscalTicketNo: Int!
     *   posDateTime: String!
     *   posSwVersion: String!
     *   terminalId: String
     *   deviceId: String!
     *   bookingPeriodId: String!
     *   bookingDate: String!
     *   ticketMedium: TicketMedium!
     *   employeeId: String!
     *   reportNo: Int!
     *   reportBookingDate: String!
     *   posDevices: [PosDeviceInput]!
     *   fdmDevices: [FdmDeviceInput]!
     *   turnover: TurnoverInput!
     * }
     */
    generateTurnoverZInput() {
        return {
            ...this.generateTurnoverXInput(),
            reportNo: this.turnoverData.reportNo,
            reportBookingDate: this.turnoverData.reportBookingDate,
        };
    }

    /**
     * @returns {TurnoverInput} The turnover input object.
     * @description
     * Generates the turnover data for the turnover X report.
     *
     * input TurnoverInput {
     *   transactions: [EventTotalInput!]!
     *   departments: [DepartmentTotalInput!]!
     *   vats: [VatTotalInput!]!
     *   payments: [PaymentTotalInput!]!
     *   drawersOpenCount: Int! = 0
     *   negQuantities: [NegQuantityTotalInput!]!
     *   priceChanges: [PriceChangeTotalInput!]!
     *   invoices: [InvoiceTotalInput!]
     * }
     */
    generateTurnoverInput() {
        return {
            transactions: this.turnoverData.turnoverTransactions,
            departments: this.turnoverData.departments,
            vats: this.turnoverData.vats,
            payments: this.turnoverData.l10_be_payments,
            drawersOpenCount: this.turnoverData.drawersOpenCount,
            negQuantities: this.turnoverData.negQuantities,
            priceChanges: this.turnoverData.priceChanges,
            invoices: this.turnoverData.l10_be_invoices,
        };
    }

    /**
     * @returns {ReportUserXInput} The user X report input object.
     * @description
     * This function generates the input data required for the User X report in the Blackbox FDM.
     *
     * input ReportUserXInput {
     *   language: Language!
     *   vatNo: String!
     *   estNo: String!
     *   posId: String!
     *   posFiscalTicketNo: Int!
     *   posDateTime: String!
     *   posSwVersion: String!
     *   terminalId: String!
     *   deviceId: String!
     *   bookingPeriodId: String!
     *   bookingDate: String!
     *   ticketMedium: TicketMedium!
     *   employeeId: String!
     *   posDevices: [PosDeviceInput!]!
     *   fdmDevices: [FdmDeviceInput!]!
     *   users: [UserItemInput!]!
     * }
     */
    generateUserXInput() {
        return {
            ...this.generateCommonInput(),
            ticketMedium: "DIGITAL",
            posDevices: this.userData.posDevices,
            fdmDevices: this.userData.fdmDevices,
            users: this.extractFdmData(this.userData.users),
        };
    }

    /**
     * @returns {ReportUserZInput} The user Z report input object.
     * @description
     * This function generates the input data required for the User Z report in the Blackbox FDM.
     *
     * input ReportUserZInput {
     *   language: Language!
     *   vatNo: String!
     *   estNo: String!
     *   posId: String!
     *   posFiscalTicketNo: Int!
     *   posDateTime: String!
     *   posSwVersion: String!
     *   terminalId: String
     *   deviceId: String!
     *   bookingPeriodId: String!
     *   bookingDate: String!
     *   ticketMedium: TicketMedium!
     *   employeeId: String!
     *   reportNo: Int!
     *   reportBookingDate: String!
     *   posDevices: [PosDeviceInput!]!
     *   fdmDevices: [FdmDeviceInput!]!
     *   users: [UserItemInput!]!
     * }
     */
    generateUserZInput() {
        return {
            ...this.generateUserXInput(),
            reportNo: this.userData.reportNo,
            reportBookingDate: this.userData.reportBookingDate,
        };
    }

    /**
     * @param {Array<Object>} data - The array of data objects to extract FDM data from.
     * @returns {Array<Object>} The extracted FDM data.
     * @description
     * This function extracts FDM-related data from the provided array of data objects by filtering out
     * any keys that start with an underscore ("_").
     */
    extractFdmData(data) {
        return data.map((item) =>
            Object.fromEntries(Object.entries(item).filter(([key]) => !key.startsWith("_")))
        );
    }
}
