import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import { PosBlackboxBe } from "@l10n_be_pos_blackbox/common/blackbox/blackbox";
import { rpc } from "@web/core/network/rpc";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

/** Notes:
 *  We only make blackbox signature for 'kiosk' self-ordering mode, orders from 'mobile' are notified to the POS and send to the blackbox (see 'getSelfOrderToPrint()')
 *  We have to be able to sign orders from the kiosk because we want the signature in order to print the receipt (with signature) directly at the Kiosk..
 */
patch(SelfOrder.prototype, {
    async setup(...args) {
        await super.setup(...args);
        if (this.config.l10n_be_blackbox_be_id && this.config.self_ordering_mode === "kiosk") {
            this.blackbox = new PosBlackboxBe({
                models: this.models,
                data: this.data,
                dialog: this.dialog,
                notification: this.notification,
                ensureClockedInFunc: this.ensureClockedInKiosk.bind(this),
                showBlackboxErrorPopupFunc: this.showBlackboxErrorPopupKiosk.bind(this),
                handleBlackboxSignatureFunc: this.handleBlackboxSignatureKiosk.bind(this),
            });
            this.doingClockIn = false;
            await this.clock(true);
        }
    },
    get selfOrderingDefaultUserInsz() {
        return this.session.config_id._self_ordering_default_user_insz;
    },
    get defaultUser() {
        return this.session.config_id.self_ordering_default_user_id;
    },
    isUserClockedIn() {
        const defaultUser = this.defaultUser;
        return this.session.l10n_be_users_clocked_ids.includes(defaultUser);
    },
    async clock(clockIn = true) {
        const isClocked = this.isUserClockedIn();
        let result = false;
        if (!isClocked && clockIn) {
            result = await this.blackbox.signWorkIn.sign(
                this.models,
                this.selfOrderingDefaultUserInsz
            );
        } else if (isClocked && !clockIn) {
            result = await this.blackbox.signWorkOut.sign(
                this.models,
                this.selfOrderingDefaultUserInsz
            );
        }
        if (result) {
            clockIn === true
                ? (this.session.l10n_be_users_clocked_ids = [this.defaultUser])
                : (this.session.l10n_be_users_clocked_ids = []);
            await rpc(`/l10n_be_pos_blackbox_self_order/clock/`, {
                access_token: this.access_token,
                config_id: this.config.id,
                session_id: this.session.id,
                clock_in: clockIn,
            });
        }
    },
    async handleKioskSessionStatusChange(status) {
        super.handleKioskSessionStatusChange(status);
        if (this.config.l10n_be_blackbox_be_id) {
            if (status === "closed") {
                const sessionId = this.session.id;
                const saleDetails = await rpc(`/l10n_be_pos_blackbox_self_order/get_sale_details`, {
                    access_token: this.access_token,
                    config_id: this.config.id,
                    session_id: sessionId,
                });

                const userReportData = await rpc(
                    `/l10n_be_pos_blackbox_self_order/get_l10n_be_user_report_data`,
                    {
                        access_token: this.access_token,
                        config_id: this.config.id,
                        session_id: sessionId,
                    }
                );
                await this.clock(false);

                this.blackbox.signReportTurnoverZ.signWithDelay(
                    this.models,
                    saleDetails,
                    sessionId,
                    this.selfOrderingDefaultUserInsz
                );

                this.blackbox.signReportUserZ.signWithDelay(
                    this.models,
                    userReportData,
                    sessionId,
                    this.selfOrderingDefaultUserInsz
                );

                rpc(`/l10n_be_pos_blackbox_self_order/generate_l10n_z_reports_attachments`, {
                    access_token: this.access_token,
                    config_id: this.config.id,
                    session_id: sessionId,
                    sale_details: saleDetails,
                    user_report_data: userReportData,
                });
            }
        }
    },
    async ensureClockedInKiosk(name) {
        if (name != "signWorkIn" && !this.doingClockIn && !this.isUserClockedIn()) {
            try {
                this.doingClockIn = true;
                await this.clock(true);
            } finally {
                this.doingClockIn = false;
            }
        }
    },
    async showBlackboxErrorPopupKiosk(error, data, name) {
        this.dialog.closeAll();
        this.dialog.add(AlertDialog, {
            title: _t("Blackbox Error - %s", name),
            body: _t(error.getMessage()),
        });
        console.warn("Blackbox errors:", error.errors, data, name);
    },
    async handleBlackboxSignatureKiosk(payload) {
        await rpc(`/l10n_be_pos_blackbox_self_order/handle_blackbox_signature/`, {
            access_token: this.access_token,
            config_id: this.config.id,
            session_id: this.session.id,
            payload,
        });
    },
    showDownloadButton(order) {
        if (!this.config.l10n_be_pos_id) {
            return super.showDownloadButton(order);
        }
        // TODO-manv: FW-19.1: directly contact OBOX via backend to sign mobile orders
        // Make receipt downloadable if the order is signed
        return false;
    },
});
