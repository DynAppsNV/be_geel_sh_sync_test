import { PosSession } from "@point_of_sale/../tests/unit/data/pos_session.data";
import { patch } from "@web/core/utils/patch";

patch(PosSession.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "l10n_be_employees_clocked_ids"];
    },
});

PosSession._records = [
    {
        ...PosSession._records[0],
        l10n_be_employees_clocked_ids: [],
    },
];
