import { ProductCombo } from "@point_of_sale/../tests/unit/data/product_combo.data";

ProductCombo._records = [
    {
        id: 1,
        name: "Starters",
        combo_item_ids: [1],
        base_price: 20.0,
        qty_free: 1,
        qty_max: 1,
    },
    {
        id: 2,
        name: "Main Dishes",
        combo_item_ids: [2],
        base_price: 28.0,
        qty_free: 1,
        qty_max: 1,
    },
    {
        id: 3,
        name: "Drink",
        combo_item_ids: [3],
        base_price: 24.0,
        qty_free: 1,
        qty_max: 1,
    },
    // Combos dedicated to "Business Menu All-In Multi Qty": starter qty=2, drink qty=3, main qty=1
    {
        id: 4,
        name: "Multi Starters",
        combo_item_ids: [4],
        base_price: 20.0,
        qty_free: 2,
        qty_max: 2,
    },
    {
        id: 5,
        name: "Multi Drink",
        combo_item_ids: [5],
        base_price: 24.0,
        qty_free: 3,
        qty_max: 3,
    },
    {
        id: 6,
        name: "Single Main",
        combo_item_ids: [6],
        base_price: 28.0,
        qty_free: 1,
        qty_max: 1,
    },
];
