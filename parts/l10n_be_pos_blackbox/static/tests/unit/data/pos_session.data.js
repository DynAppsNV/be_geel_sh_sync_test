import { PosSession } from "@point_of_sale/../tests/unit/data/pos_session.data";
import { patch } from "@web/core/utils/patch";

patch(PosSession.prototype, {
    _load_pos_data_models() {
        return [...super._load_pos_data_models(), "pos.blackbox.be"];
    },

    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "l10n_be_users_clocked_ids", "booking_period_id"];
    },

    set_work_in_out_cashier(self, cashierId, action = "in") {
        const session = this.browse(self)[0];
        const isHr = this.env["pos.config"].browse(session.config_id)[0].module_pos_hr;
        const field = isHr ? "l10n_be_employees_clocked_ids" : "l10n_be_users_clocked_ids";
        const clockedIds = session[field] || [];
        const isClocked = clockedIds.includes(cashierId);
        if (action === "in" && !isClocked) {
            this.write([self], {
                [field]: [...clockedIds, cashierId],
                ...(isHr ? { employee_id: cashierId } : {}),
            });
        } else if (action === "out" && isClocked) {
            const newClockedIds = clockedIds.filter((id) => id !== cashierId);
            this.write([self], {
                [field]: newClockedIds.length ? newClockedIds : false,
            });
        }
    },

    work_out_all_cashiers(self) {
        const session = this.browse(self)[0];
        const isHr = this.env["pos.config"].browse(session.config_id)[0].module_pos_hr;
        const field = isHr ? "l10n_be_employees_clocked_ids" : "l10n_be_users_clocked_ids";
        const clockedIds = session[field] || [];
        this.write([self], {
            [field]: false,
        });
        return clockedIds.map((c) => c.l10n_be_insz_or_bis_number);
    },
});

PosSession._records = [
    {
        id: 1,
        name: "Main POS/00001",
        user_id: 2,
        config_id: 1,
        start_at: "2025-07-23 12:23:54",
        stop_at: false,
        payment_method_ids: [1, 2],
        state: "opened",
        update_stock_at_closing: false,
        cash_register_balance_start: 0.0,
        access_token: "0ca2ebb7-5f77-4d03-99a9-77b5673ab248",
        l10n_be_N_event_counter: 0,
        l10n_be_I_event_counter: 0,
        l10n_be_users_clocked_ids: [],
        booking_period_id: "0ca2ebb7-5f77-4d03-99a9-77b5673ab248",
    },
];
