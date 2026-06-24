import { ResUsers } from "@point_of_sale/../tests/unit/data/res_users.data";
import { patch } from "@web/core/utils/patch";

patch(ResUsers.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "l10n_be_insz_or_bis_number"];
    },
});

ResUsers._records = ResUsers._records.map((user) => ({
    ...user,
    company_id: 2,
    company_ids: [2],
    l10n_be_insz_or_bis_number: "97121722222",
}));
