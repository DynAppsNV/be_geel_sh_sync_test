import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useEffect, useState } from "@odoo/owl";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { ProviderLogo } from "./provider_logo";
const { DateTime } = luxon;

const MS_PER_SEC = 1000;
const SYNC_FILTER = "SYNCED";
const CANCELLED_FILTER = "CANCELLED";

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.state = useState({
            ...this.state,
            isPlatformOrderMode: false,
            currentTime: DateTime.now(),
        });

        useEffect(
            () => {
                const interval = setInterval(() => {
                    this.state.currentTime = DateTime.now();
                }, MS_PER_SEC);
                return () => clearInterval(interval);
            },
            () => []
        );

        useEffect(
            () => {
                if (this.pos.selectedOrderUuid) {
                    this.state.selectedOrderUuid = this.pos.selectedOrderUuid;
                }
            },
            () => [this.pos.selectedOrderUuid]
        );
    },

    // =========================================================================
    // EVENT HANDLERS
    // =========================================================================

    /** @override */
    onPresetSelected(preset) {
        this.state.isPlatformOrderMode = false;
        super.onPresetSelected(...arguments);
    },

    onPlatformOrderSelected() {
        this.state.selectedPreset = null;
        this.state.isPlatformOrderMode = !this.state.isPlatformOrderMode;
    },

    onDblClickOrder(order) {
        if (order.isPlatformOrder) {
            return;
        }
        super.onDblClickOrder(...arguments);
    },

    async onMarkFoodReadyClicked(order) {
        const rpcCall = this.pos.data.call("pos.order", "platform_order_status_update_from_ui", [
            order.id,
            "food_ready",
        ]);
        const result = await this._handleRpc(order, rpcCall);
        if (result.success) {
            order.platform_order_food_ready = true;
        }
    },

    async onAcceptOrderClicked(order) {
        const rpcCall = this.pos.data.call("pos.order", "platform_order_status_update_from_ui", [
            order.id,
            "accept",
        ]);
        await this._handleRpc(order, rpcCall, { block: true });
    },

    // =========================================================================
    // GETTERS (COMPUTED PROPERTIES)
    // =========================================================================

    get showAcceptOrderButton() {
        const order = this.getSelectedOrder();
        return order?.isPlatformOrder && order.platform_order_status === "new";
    },

    get selectedOrderExpiration() {
        const order = this.getSelectedOrder();
        if (!order?.isPlatformOrder || !order.platform_order_provider_id.valid_for_seconds) {
            return false;
        }

        const expirationMs = order.platform_order_provider_id.valid_for_seconds * MS_PER_SEC;
        const orderTime = DateTime.fromISO(order.create_date);
        const timeDiffMs = this.state.currentTime.diff(orderTime).toMillis();
        const remainingMs = Math.max(0, expirationMs - timeDiffMs);

        return {
            isExpired: remainingMs === 0,
            formattedRemainingTime: DateTime.fromMillis(remainingMs).toFormat("mm:ss"),
            remainingTimePercentage: (remainingMs / expirationMs) * 100,
        };
    },

    /** @override */
    get isOrderSynced() {
        const order = this.getSelectedOrder();
        return super.isOrderSynced && order?.platform_order_status !== "cancelled";
    },

    // =========================================================================
    // FILTERING LOGIC
    // =========================================================================

    /** @override */
    activeOrderFilter(order) {
        const isPlatformOrderActive =
            order.isPlatformOrder &&
            !["delivered", "cancelled", "failed"].includes(order.platform_order_status) &&
            order.uiState.displayed;
        return super.activeOrderFilter(...arguments) || isPlatformOrderActive;
    },

    /** @override */
    _getFilterOptions() {
        const filters = super._getFilterOptions(...arguments);
        filters.set(CANCELLED_FILTER, { text: _t("Cancelled") });
        return filters;
    },

    /** @override */
    getFilteredOrderList() {
        let orderList = super.getFilteredOrderList(...arguments);

        if (this.state.filter === SYNC_FILTER) {
            orderList = orderList.filter((order) => order.platform_order_status !== "cancelled");
        }

        if (this.state.filter === CANCELLED_FILTER) {
            // Filter all the finalized orders again for cancelled platform orders
            // Ignore other filters first because it is complicated to filter
            return this.pos.models["pos.order"].filter(
                (order) => order.finalized && order.platform_order_status === "cancelled"
            );
        }

        if (this.state.isPlatformOrderMode) {
            return orderList.filter((order) => order.isPlatformOrder);
        }

        return orderList;
    },

    /** @override */
    getStatus(order) {
        if (!order.isPlatformOrder) {
            return super.getStatus(order);
        }

        const statusMap = {
            new: _t("New"),
            accepted: _t("Ongoing"),
            collected: _t("Paid"),
            delivered: _t("Paid"),
        };
        return statusMap[order.platform_order_status] || "";
    },

    // =========================================================================
    // PRIVATE HELPERS
    // =========================================================================

    async _handleRpc(order, rpcPromise, { block = false } = {}) {
        if (block) {
            this.ui.block();
        }
        try {
            const result = await rpcPromise;
            if (!result.success) {
                this.pos.notification.add(result.message, {
                    type: "danger",
                    title: _t("Order Reference: %s", order.platform_order_ref),
                });
            }
            return result;
        } catch (error) {
            logPosMessage("TicketScreen", "_handleRpc", "Error occurred", false, [error]);

            let message = _t("An unknown error occurred.");
            if (!navigator.onLine) {
                message = _t("Device is offline. Platform order requires an internet connection.");
            }

            this.pos.notification.add(message, {
                type: "danger",
                title: _t("Order Reference: %s", order.platform_order_ref),
            });
            return { success: false, message: _t("Unknown error") };
        } finally {
            if (block) {
                this.ui.unblock();
            }
        }
    },
});

patch(TicketScreen, {
    components: { ...TicketScreen.components, ProviderLogo },
});
