import { ProductComboItem } from "@point_of_sale/../tests/unit/data/product_combo_item.data";

ProductComboItem._records = [
    {
        id: 1,
        combo_id: 1,
        product_id: 9,
        extra_price: 0.0,
    },
    {
        id: 2,
        combo_id: 2,
        product_id: 10,
        extra_price: 0.0,
    },
    {
        id: 3,
        combo_id: 3,
        product_id: 8,
        extra_price: 0.0,
    },
    // Combo items for "Business Menu All-In Multi Qty"
    {
        id: 4,
        combo_id: 4,
        product_id: 9, // Carpaccio Beef (starters)
        extra_price: 0.0,
    },
    {
        id: 5,
        combo_id: 5,
        product_id: 8, // Matching Wines (drink)
        extra_price: 0.0,
    },
    {
        id: 6,
        combo_id: 6,
        product_id: 10, // Burger of the Chef (main)
        extra_price: 0.0,
    },
];
