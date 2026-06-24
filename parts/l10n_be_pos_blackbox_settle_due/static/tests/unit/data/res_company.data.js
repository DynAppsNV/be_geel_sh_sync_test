import { ResCompany } from "@point_of_sale/../tests/unit/data/res_company.data";

ResCompany._records = ResCompany._records.map((record) => ({
    ...record,
    currency_id: 125,
    country_id: 20,
    account_fiscal_country_id: 20,
}));
