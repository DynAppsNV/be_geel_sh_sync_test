import { ProductProduct } from "@point_of_sale/../tests/unit/data/product_product.data";

ProductProduct._records = [
    ...ProductProduct._records,
    {
        id: 100,
        product_tmpl_id: 100,
        lst_price: 100,
        standard_price: 0,
        display_name: "Gift card",
        product_tag_ids: [],
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
    },
];
