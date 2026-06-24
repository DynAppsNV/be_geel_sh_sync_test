import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    deposit_product_id: 205,
    settle_due_product_id: 206,
    settle_invoice_product_id: 207,
    payment_method_ids: [...record.payment_method_ids, 3],
    company_id: 253,
}));
