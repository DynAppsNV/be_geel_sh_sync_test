import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

PosConfig._records = [
    {
        ...PosConfig._records[0],
        module_pos_hr: true,
        basic_employee_ids: [3],
        advanced_employee_ids: [2],
    },
];
