import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { L10nBeBlackboxErrorPopup } from "@l10n_be_pos_blackbox/common/blackbox/utils/error_popup/error_popup";
import { serializeDateTime } from "@web/core/l10n/dates";
import { CustomSelectCreateDialog } from "@point_of_sale/app/components/custom_select_create_dialog/custom_select_create_dialog";
import { uuidv4 } from "@point_of_sale/utils";
import { OpeningDeviceErrorPopup } from "@l10n_be_pos_blackbox/point_of_sale/components/popups/opening_device_error_popup/opening_device_error_popup";
import { MustClockInPopup } from "@l10n_be_pos_blackbox/point_of_sale/components/popups/must_clock_in_popup/must_clock_in_popup";
import { PosBlackboxBe } from "@l10n_be_pos_blackbox/common/blackbox/blackbox";
import { deepEqual } from "@web/core/utils/objects";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { user } from "@web/core/user";

const CONSOLE_COLOR = "#62da56";

patch(PosStore.prototype, {
    async setup(env, deps) {
        await super.setup(...arguments);
        if (this.blackbox.isActive) {
            this.doingClockIn = false;
        }
        this.isDeviceAuthorized = await this.ensureBlackboxDeviceLog();
    },
    async afterProcessServerData() {
        this.blackbox = new PosBlackboxBe({
            models: this.models,
            data: this.data,
            dialog: this.dialog,
            notification: this.notification,
            ensureClockedInFunc: this.ensureClockedInPos.bind(this),
            showBlackboxErrorPopupFunc: this.showBlackboxErrorPopupPos.bind(this),
            handleBlackboxSignatureFunc: this.handleBlackboxSignature.bind(this),
        });

        await super.afterProcessServerData(...arguments);
    },
    async ensureBlackboxDeviceLog() {
        const deviceKey = "l10n_be_pos_blackbox-device-id-identifier";

        let device = localStorage.getItem(deviceKey);
        if (!device) {
            device = uuidv4();
            localStorage.setItem(deviceKey, device);
        }
        const result = await this.data.call("pos.blackbox.log.device", "log_device", [
            this.session.config_id.id,
            device,
        ]);
        if (!result) {
            this.dialog.closeAll();
            this.dialog.add(OpeningDeviceErrorPopup);
            return false;
        }
        return true;
    },
    shouldShowOpeningControl() {
        return this.isDeviceAuthorized && super.shouldShowOpeningControl(...arguments);
    },
    isCashierClockedIn(cashierId = this.getCashier().id) {
        return this.session.l10n_be_users_clocked_ids.map((u) => u.id).includes(cashierId);
    },
    async handleClockInOut(cashier, action = "in") {
        if (this.blackbox.isActive && this.session.state === "opened") {
            let result;
            // Cashier can either be "res.users" or "hr.employee"
            const cashierClocked = this.isCashierClockedIn(cashier.id);

            if (!cashierClocked && action === "in") {
                result = await this.blackbox.signWorkIn.sign(
                    this.models,
                    cashier.l10n_be_insz_or_bis_number
                );
            } else if (cashierClocked && action === "out") {
                result = await this.blackbox.signWorkOut.sign(
                    this.models,
                    cashier.l10n_be_insz_or_bis_number
                );
            }

            if (result) {
                if (!this.config.module_pos_hr) {
                    action === "in"
                        ? (this.session.l10n_be_users_clocked_ids = [cashier])
                        : (this.session.l10n_be_users_clocked_ids = []);
                }
                await this.data.call("pos.session", "set_work_in_out_cashier", [
                    this.session.id,
                    cashier.id,
                    action,
                ]);
            }

            return Boolean(result);
        }

        return true;
    },
    setCashier(cashier) {
        if (this.blackbox?.isActive) {
            this.handleClockInOut(cashier, "in");
        }
        super.setCashier(cashier);
    },
    resetCashier() {
        const cashier = this.getCashier();
        if (cashier && this.blackbox.isActive) {
            this.handleClockInOut(cashier, "out");
        }
        return super.resetCashier(...arguments);
    },
    async workOutAllCashiers() {
        if (this.blackbox.isActive && this.session.state === "opened") {
            const clockedOutCashiersInsz = await this.data.call(
                "pos.session",
                "work_out_all_cashiers",
                [this.session.id]
            );
            for (const cashierInsz of clockedOutCashiersInsz) {
                await this.blackbox.signWorkOut.sign(this.models, cashierInsz);
            }
            if (!this.config.module_pos_hr) {
                this.session.l10n_be_users_clocked_ids = [];
            }
        }
    },
    async preSyncAllOrders(orders) {
        if (!this.blackbox.isActive || orders.length === 0 || orders[0].l10n_be_short_signature) {
            return await super.preSyncAllOrders(...arguments);
        }
        const order = orders[0];
        const usr = this.getCashier().l10n_be_insz_or_bis_number;
        const printerUrl = this.printer.hardware_proxy.printer?.url;

        // Signature that must happen before syncing
        if (order.isPartialRefund) {
            await this.blackbox.signSaleRefundPartial.sign(order, usr, printerUrl);
        } else if (order.isRefund) {
            await this.blackbox.signSaleRefund.sign(order, usr, printerUrl);
        } else if (order.state === "paid") {
            await this.blackbox.signSale.sign(order, usr, printerUrl);
        } else {
            await this.blackbox.signOrder.sign(order, usr);
        }

        // Only sync draft orders & the one that have been signed
        const processedOrder =
            !order.finalized ||
            (order.l10n_be_short_signature && ["paid", "done"].includes(order.state));

        if (processedOrder) {
            order.resetDeletedLines();
            order.lines.forEach((line) => line.resetMaxValues());
        }

        return processedOrder ? super.preSyncAllOrders([order]) : super.preSyncAllOrders([]);
    },
    async postSyncAllOrders(orders) {
        super.postSyncAllOrders(orders);
        if (
            this.blackbox.isActive &&
            orders.length === 1 &&
            orders[0].l10n_be_short_signature &&
            orders[0].to_invoice &&
            !orders[0].l10n_be_I_total_counter
        ) {
            const usr = this.getCashier().l10n_be_insz_or_bis_number;
            // This must be done after syncing because we need the order account move to be created to sign the invoice
            await this.blackbox.signInvoice.sign(orders[0], usr);
        }
    },
    async prepareOrderTransfer(order, destinationTable) {
        if (!this.blackbox.isActive) {
            return await super.prepareOrderTransfer(...arguments);
        }
        const originalTable = order.table_id;
        const oldCostCenter = order.generateCostCenterInput();
        const res = await super.prepareOrderTransfer(...arguments);
        // In this case we are transferring/merging to another table (without order), so no order is created we just change the source order's table_id
        if (!res && destinationTable.rootTable.id !== originalTable?.id) {
            const usr = this.getCashier().l10n_be_insz_or_bis_number;
            const newCostCenter = order.generateCostCenterInput();
            await this.blackbox.signCostCenterChange.signCostCenterChange(
                order,
                oldCostCenter,
                newCostCenter,
                usr
            );
        }
        return res;
    },
    async _mergeLines(orphanLine, destinationLine, destOrder, sourceOrder, mergedCourses) {
        const res = await super._mergeLines(...arguments);
        if (this.blackbox.isActive) {
            this.sourceLinesNextUuidMap[orphanLine.uuid] = res;
        }
        return res;
    },
    async _mergeOrders(sourceOrder, destinationOrder) {
        if (!this.blackbox.isActive || !destinationOrder) {
            return super._mergeOrders(...arguments);
        }
        const usr = this.getCashier().l10n_be_insz_or_bis_number;
        // This is called when a merge/transfer is done to a table with an existing order
        const sourceOrderTransLines = sourceOrder.l10n_be_last_transaction_by_line || {};
        const destOrderTransLines = destinationOrder.l10n_be_last_transaction_by_line || {};
        const signed = await this.blackbox.signCostCenterChange.signCostCenterChange(
            sourceOrder,
            sourceOrder.generateCostCenterInput(),
            destinationOrder.generateCostCenterInput(),
            usr
        );
        // We set this flag to avoid triggering a useless signOrder when it will be deleted (see _onBeforeDeleteOrder)
        sourceOrder.uiState.isTransferred = true;
        // We keep track of the source order lines uuids and the corresponding destination line uuids (after merge)
        this.sourceLinesNextUuidMap = {};
        const srcOrderDiscountPc = sourceOrder.globalDiscountPc;
        const destOrderDiscountPcBeforeMerge = destinationOrder.globalDiscountPc;
        const res = await super._mergeOrders(...arguments);
        // Transfer groupingId line states from the source order to the destination order
        // for lines that could not be merged (orphan lines that received a fresh UUID on
        // the destination order).  Merged lines already carry the destination UUID, so
        // their entry in l10n_be_grouping_id.lines already exists on destinationOrder and
        // should NOT be overwritten.
        if (sourceOrder.l10n_be_grouping_id) {
            if (!destinationOrder.l10n_be_grouping_id) {
                destinationOrder.l10n_be_grouping_id = {
                    groupingIdCount: 0,
                    globalDiscountGId: null,
                    roundingAdaptationGId: null,
                    lines: {},
                };
            }
            const srcGroupingState = sourceOrder.l10n_be_grouping_id;
            const destGroupingState = destinationOrder.l10n_be_grouping_id;
            const srcLines = srcGroupingState.lines || {};
            for (const [oldUuid, newUuid] of Object.entries(this.sourceLinesNextUuidMap)) {
                // Only copy if the destination does not already know about this UUID
                // (i.e. the line was transferred as-is, not merged into an existing line)
                if (srcLines[oldUuid] && !destGroupingState.lines[newUuid]) {
                    destGroupingState.lines[newUuid] = { ...srcLines[oldUuid] };
                }
            }
            // Ensure the destination counter is at least as high as the source counter
            // so that IDs allocated on the source order are never recycled.
            destGroupingState.groupingIdCount = Math.max(
                destGroupingState.groupingIdCount,
                srcGroupingState.groupingIdCount
            );
        }
        if (signed) {
            // If the destination have a global discount, we apply it before the next signOrder (that will be triggered inside `syncAllOrders`, see 'mergeOrders' inside 'pos_restaurant')
            const destOrderDiscountPc = destinationOrder.globalDiscountPc;
            if (destOrderDiscountPc) {
                await this.applyDiscount(destOrderDiscountPc, destinationOrder);
            }
            // If the GD is different of both order is different, we have to make a 'PRICE_CHANGE' correction (cancel old GD, apply new one)
            if (destOrderDiscountPcBeforeMerge != srcOrderDiscountPc) {
                if (srcOrderDiscountPc === destOrderDiscountPc) {
                    // If the applied discount of the merged order is the same as the source order, we need to correct old destination order lines
                    await this.blackbox.signOrder.signGlobalDiscountChange(
                        destinationOrder,
                        destOrderTransLines,
                        false,
                        usr
                    );
                } else if (destOrderDiscountPcBeforeMerge === destOrderDiscountPc) {
                    // If the applied discount of the merged order is the same as the destination order, we need to correct source order lines
                    await this.blackbox.signOrder.signGlobalDiscountChange(
                        destinationOrder,
                        sourceOrderTransLines,
                        this.sourceLinesNextUuidMap,
                        usr
                    );
                }
            }
            // Update the last transaction by line of the orders
            sourceOrder.l10n_be_last_transaction_by_line = {};
            destinationOrder.updateLastTransactionLines();
        }
        return res;
    },
    async syncRestoredOrders(order, newOrder) {
        if (!this.blackbox.isActive) {
            return await super.syncRestoredOrders(...arguments);
        }
        const usr = this.getCashier().l10n_be_insz_or_bis_number;
        await this.blackbox.signCostCenterChange.signOrderChange(order, newOrder, usr);
        return await super.syncRestoredOrders(...arguments);
    },
    async transferOrder(orderUuid, destinationTable, destinationOrder) {
        if (!this.blackbox.isActive) {
            return super.transferOrder(...arguments);
        }
        const sourceOrder = this.models["pos.order"].getBy("uuid", orderUuid);
        const usr = this.getCashier().l10n_be_insz_or_bis_number;
        // Before transferring orders, we push the potential changes of the source order to the blackbox
        await this.blackbox.signOrder.sign(sourceOrder, usr);
        return super.transferOrder(...arguments);
    },
    async mergeTableOrders(orderUuid, destinationTable) {
        if (!this.blackbox.isActive) {
            return super.mergeTableOrders(...arguments);
        }
        const sourceOrder = this.models["pos.order"].getBy("uuid", orderUuid);
        const usr = this.getCashier().l10n_be_insz_or_bis_number;
        // Before merging orders, we push the potential changes of the source order to the blackbox
        await this.blackbox.signOrder.sign(sourceOrder, usr);
        return super.mergeTableOrders(...arguments);
    },
    async _onBeforeDeleteOrder(order) {
        const result = await super._onBeforeDeleteOrder(...arguments);
        if (
            this.blackbox.isActive &&
            !order.uiState.isTransferred &&
            !order.uiState.isDeleteInProgress
        ) {
            // Flag to avoid duplicate blackbox call if we try to quickly delete the order multiple times from ticket screen
            order.uiState.isDeleteInProgress = true;
            try {
                const usr = this.getCashier().l10n_be_insz_or_bis_number;
                await this.finalizeOrderCorrection(order);
                await this.blackbox.signOrder.signCanceledOrder(order, usr);
                await this.blackbox.signSale.signEmptyOrder(
                    order,
                    usr,
                    this.printer.hardware_proxy.printer?.url
                );
                order.uiState.isEmptyReceipt = true;
                await this.printer.print(OrderReceipt, {
                    order: order,
                    empty_receipt: true,
                });
            } finally {
                order.uiState.isDeleteInProgress = false;
            }
        }
        return result;
    },
    async finalizeOrderCorrection(order) {
        const correction = {};
        for (const line of order.lines) {
            if (line.combo_parent_id) {
                continue;
            }
            if (
                (line.uiState.maxQuantity && line.qty < line.uiState.maxQuantity) ||
                (line.uiState.maxUnitPrice &&
                    line.blackboxPriceUnitNoDiscount < line.uiState.maxUnitPrice)
            ) {
                correction[line.uuid] = {
                    qty: line.uiState.maxQuantity || line.qty,
                    priceUnit: line.uiState.maxUnitPrice || line.blackboxPriceUnitNoDiscount,
                    discount: line.discount,
                    globalDiscount: line.order_id.globalDiscountPc,
                    line: line,
                };
            }
        }
        if (Object.keys(order.uiState.deletedLines).length) {
            for (const [lineUuid, initialTransLine] of Object.entries(order.uiState.deletedLines)) {
                correction[lineUuid] = {
                    initialTransLine,
                };
            }
        }
        if (Object.keys(correction).length) {
            await this.blackbox.signOrder.signOrderWithCorrection(
                order,
                correction,
                this.getCashier().l10n_be_insz_or_bis_number
            );
        }
        order.resetDeletedLines();
        order.lines.forEach((line) => line.resetMaxValues());
    },
    async signTurnoverReport(sessionId = this.session.id, state = this.session.state) {
        const saleDetails = await this.data.call(
            "report.point_of_sale.report_saledetails",
            "get_sale_details",
            [false, false, false, [sessionId]]
        );
        if (state === "closed") {
            if (saleDetails.l10n_be_turnover_z_report_fdm_ref) {
                this.blackbox.signCopy.signReportWithDelay(
                    this.models,
                    saleDetails.l10n_be_turnover_z_report_fdm_ref,
                    this.getCashier().l10n_be_insz_or_bis_number
                );
            } else {
                this.blackbox.signReportTurnoverZ.signWithDelay(
                    this.models,
                    saleDetails,
                    sessionId,
                    this.getCashier().l10n_be_insz_or_bis_number
                );
            }
        } else {
            this.blackbox.signReportTurnoverX.signWithDelay(
                this.models,
                saleDetails,
                this.getCashier().l10n_be_insz_or_bis_number
            );
        }
    },
    async signUserReport(sessionId = this.session.id, state = this.session.state) {
        const userReportData = await this.data.call("pos.session", "get_l10n_be_user_report_data", [
            sessionId,
        ]);
        if (state === "closed") {
            if (userReportData.l10n_be_user_z_report_fdm_ref) {
                this.blackbox.signCopy.signReportWithDelay(
                    this.models,
                    userReportData.l10n_be_user_z_report_fdm_ref,
                    this.getCashier().l10n_be_insz_or_bis_number
                );
            } else {
                this.blackbox.signReportUserZ.signWithDelay(
                    this.models,
                    userReportData,
                    sessionId,
                    this.getCashier().l10n_be_insz_or_bis_number
                );
            }
        } else {
            this.blackbox.signReportUserX.signWithDelay(
                this.models,
                userReportData,
                this.getCashier().l10n_be_insz_or_bis_number
            );
        }
    },
    async signExternalOrder(order) {
        const usr = this.getCashier().l10n_be_insz_or_bis_number;
        await this.blackbox.signSale.sign(order, usr, this.printer.hardware_proxy.printer?.url);
        if (order.l10n_be_short_signature) {
            this.data.write("pos.order", [order.id], {
                l10n_be_short_signature: order.l10n_be_short_signature,
                l10n_be_event_label: order.l10n_be_event_label,
                l10n_be_event_counter: order.l10n_be_event_counter,
                l10n_be_total_counter: order.l10n_be_total_counter,
                l10n_be_fdm_id: order.l10n_be_fdm_id,
                l10n_be_fdm_date_time: serializeDateTime(order.l10n_be_fdm_date_time),
                l10n_be_pos_id: order.l10n_be_pos_id,
                l10n_be_terminal_id: order.l10n_be_terminal_id,
                l10n_be_device_id: order.l10n_be_device_id,
                l10n_be_verification_url: order.l10n_be_verification_url,
                l10n_be_pos_date_time: serializeDateTime(order.l10n_be_pos_date_time),
                l10n_be_vat_calc: order.l10n_be_vat_calc,
            });
        }
        return order;
    },
    async pay() {
        if (this.blackbox.isActive) {
            const cashier = this.getCashier();
            if (!this.isCashierClockedIn(cashier.id)) {
                this.dialog.closeAll();
                await this.dialog.add(MustClockInPopup);
                return;
            }
            const order = this.getOrder();
            const identifier = cashier.l10n_be_insz_or_bis_number;
            // We only 'signOrder' if the order has already be sent to the blackbox, otherwise it's a direct sale (no need to signOrder before the signSale)
            if (order.l10n_be_last_transaction_by_line) {
                await this.blackbox.signOrder.sign(order, identifier);
            }
        }
        return super.pay(...arguments);
    },
    async selectPartner(currentOrder = this.getOrder()) {
        if (currentOrder && this.blackbox.isActive) {
            const usr = this.getCashier().l10n_be_insz_or_bis_number;
            // We signOrder before changing its partner because we will costCenterChange afterwards (see setPartnerToCurrentOrder)
            this.blackbox.signOrder.sign(currentOrder, usr);
        }
        return super.selectPartner(...arguments);
    },
    setPartnerToCurrentOrder(partner) {
        const order = this.getOrder();
        if (!this.blackbox.isActive || !order) {
            return super.setPartnerToCurrentOrder(...arguments);
        }
        const oldCostCenter = order.generateCostCenterInput();
        const result = super.setPartnerToCurrentOrder(...arguments);
        const newCostCenter = order.generateCostCenterInput();

        if (!deepEqual(oldCostCenter, newCostCenter) && order.l10n_be_last_transaction_by_line) {
            const identifier = this.getCashier().l10n_be_insz_or_bis_number;
            this.blackbox.signCostCenterChange.signCostCenterChange(
                order,
                oldCostCenter,
                newCostCenter,
                identifier
            );
        }
        return result;
    },
    // TODO-manv: FW- 19.1: directly contact OBOX via backend to sign mobile orders
    async getSelfOrderToPrint(orderId) {
        let order = await super.getSelfOrderToPrint(...arguments);
        if (this.blackbox.isActive) {
            order = await this.signExternalOrder(order);
        }
        return order;
    },
    async ensureClockedInPos(name) {
        const cashier = this.getCashier();
        // We'll automatically clock-in the cashier if:
        // - the initial mutation is not already a 'signWorkIn'
        // - we're not already doing it (recursively)
        // - the cashier is not clocked-in yet
        if (name != "signWorkIn" && !this.doingClockIn && !this.isCashierClockedIn(cashier.id)) {
            try {
                logPosMessage(
                    "Blackbox",
                    "ensureClockedIn",
                    `${cashier.name} was not clocked in. Attempting to clock in.`,
                    CONSOLE_COLOR
                );
                this.doingClockIn = true;
                await this.handleClockInOut(cashier, "in");
            } finally {
                this.doingClockIn = false;
            }
        }
    },
    async showBlackboxErrorPopupPos(error, data, name) {
        this.dialog.closeAll();
        this.dialog.add(L10nBeBlackboxErrorPopup, {
            errors: error.errors,
            data: data,
            mutationName: name,
        });
    },
    async handleBlackboxSignature(payload) {
        const sessionId = this.session.id;
        await this.data.call("pos.session", "handle_blackbox_signature", [sessionId, payload]);
    },
    openSalesReportsList(reportService, sessionId = false) {
        const domain = [
            ["config_id", "=", this.config.id],
            ["pos_clock_in_out_ids", "!=", false],
        ];
        const callback = async (resIds) => {
            const sessionId = resIds[0];
            user.updateContext({ called_from_pos: true });
            let res;
            try {
                res = await reportService.doAction("point_of_sale.sale_details_report", [
                    sessionId,
                ]);
            } finally {
                user.updateContext({ called_from_pos: false });
            }
            if (res?.success) {
                const [session] = await this.data.read("pos.session", [sessionId], ["state"]);
                this.signTurnoverReport(
                    sessionId,
                    session.state === "closed" ? "closed" : "opened"
                );
            }
        };
        if (sessionId) {
            callback([sessionId]);
        } else {
            this.dialog.add(CustomSelectCreateDialog, {
                resModel: "pos.session",
                listViewId: this.models["ir.ui.view"].find(
                    (v) => v.name == "pos_session_reports_list_view"
                )?.id,
                noCreate: true,
                multiSelect: false,
                domain,
                context: {},
                onSelected: callback.bind(this),
            });
        }
    },
});
