import { ProductPricelistItem } from "@point_of_sale/../tests/unit/data/product_pricelist_item.data";

ProductPricelistItem._records = ProductPricelistItem._records.map((record) => ({
    ...record,
    company_id: 2,
    currency_id: 125,
}));
