import { patch } from "@web/core/utils/patch";
import { HrEmployee } from "@pos_hr/../tests/unit/data/hr_employee.data";

patch(HrEmployee.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "l10n_be_insz_or_bis_number"];
    },
});

HrEmployee._records = [
    {
        id: 2,
        name: "Fake Employee",
        user_id: false,
        l10n_be_insz_or_bis_number: "97121733333",
    },
    {
        id: 3,
        name: "Fake Employee Basic",
        user_id: false,
        l10n_be_insz_or_bis_number: "00000000097",
    },
];
