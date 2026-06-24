import { test, describe } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    getComboOrder,
    expectGeneralProperties,
    expectTransactionTotals,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { InputGenerator } from "@l10n_be_pos_blackbox/common/blackbox/utils/input_generator";

definePosModels();

describe("input generator price consistency", () => {
    /**
     *  NOTES: almost all tests succeed with 'line.blackboxPrice' but fail with 'line.displayPrice' and vice versa.
     *        You can run these tests by switching the usage of 'line.displayPrice' and 'line.blackboxPrice' inside 'input_generator.js' file
     *  We need to run all the following tests case successfully, you can run CASE 1 first, then include 2, ... by one until all tests are passing.
     *  Also all these tests should finally succeed with taxes.price_include = true (as it is now), but also with prices_include = false (need to modify the tax data inside `enterprise/l10n_be_pos_blackbox/static/tests/unit/data/account_tax.data.js`).
     *  Also go read the notes inside `enterprise/l10n_be_pos_blackbox/static/src/common/models/pos_order_line.js` for more explanations
     */
    const expectGeneralPropertiesForOrder = (order, mustHavePriceChanges = false) => {
        const generator = new InputGenerator({
            models: order.models,
            order: order,
            inszOrBisNumber: "1234567890",
        });
        const saleInput = generator.generateSignSaleInput();
        expectGeneralProperties(saleInput, {
            order: order,
            mustHavePriceChanges: mustHavePriceChanges,
            ticketMedium: "DIGITAL",
        });
        const orderInput = generator.generateSignOrderInput();
        order.updateLastTransactionLines();
        expectTransactionTotals(orderInput.transaction, order.currency);
    };
    test("[case 1] first test failing with 'line.displayPrice'", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = store.addNewOrder();
        const product = store.models["product.template"].get(15);

        await store.addLineToOrder({ product_tmpl_id: product, qty: 7 }, order);
        expectGeneralPropertiesForOrder(order);
    });

    test("[case 2] incrementally add products and update quantities", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = store.addNewOrder();

        const productTemplateIds = [15, 5, 6, 10, 4, 14, 13, 2, 3];

        for (const tmplId of productTemplateIds) {
            const product = store.models["product.template"].get(tmplId);

            await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
            expectGeneralPropertiesForOrder(order);
        }

        for (const line of order.lines) {
            line.setQuantity(line.qty + 1, false);
            expectGeneralPropertiesForOrder(order);
        }

        for (const line of order.lines) {
            line.setQuantity(5, false);
            expectGeneralPropertiesForOrder(order);
        }
    });

    test("[case 3] brutal pricing stress test with high qty", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = store.addNewOrder();

        const productTemplateIds = [15, 5, 6, 10, 4, 14, 13, 2, 3];

        for (const tmplId of productTemplateIds) {
            const product = store.models["product.template"].get(tmplId);
            await store.addLineToOrder({ product_tmpl_id: product, qty: tmplId }, order);
            expectGeneralPropertiesForOrder(order);
        }

        const bigQty = Array.from({ length: 50 }, (_, i) => i + 1);

        for (const qty of bigQty) {
            for (const line of order.lines) {
                line.setQuantity(qty, false);
                expectGeneralPropertiesForOrder(order);
            }
        }

        const randomQty = [3, 77, 12, 43, 1, 3];

        for (const qty of randomQty) {
            for (const line of order.lines) {
                line.setQuantity(qty, false);
                expectGeneralPropertiesForOrder(order);
            }
        }
    });

    test("[case 4] brutal pricing stress test with high qty with combo", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = getComboOrder(store);

        const productTemplateIds = [15, 5, 6, 10, 4, 14, 13, 2, 3];

        for (const tmplId of productTemplateIds) {
            const product = store.models["product.template"].get(tmplId);
            await store.addLineToOrder({ product_tmpl_id: product, qty: tmplId }, order);
            expectGeneralPropertiesForOrder(order);
        }

        const bigQty = Array.from({ length: 15 }, (_, i) => i + 1);

        for (const qty of bigQty) {
            for (const line of order.lines) {
                line.setQuantity(qty, false);
                expectGeneralPropertiesForOrder(order);
            }
        }

        const randomQty = [3, 27, 6, 33, 17, 3];

        for (const qty of randomQty) {
            for (const line of order.lines) {
                line.setQuantity(qty, false);
                expectGeneralPropertiesForOrder(order);
            }
        }
    });

    test("[case 5] incrementally add products and update quantities, with line price change and line discount", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = store.addNewOrder();

        const productTemplateIds = [15, 5, 6, 10, 4, 14, 13, 2, 3];

        for (const tmplId of productTemplateIds) {
            const product = store.models["product.template"].get(tmplId);

            const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
            line.price_type = "manual";
            line.setUnitPrice(product.id); // set a price change
            expectGeneralPropertiesForOrder(order, true);
        }

        for (const line of order.lines) {
            line.setQuantity(line.qty + 1, false);
            store.setDiscountFromUI(line, line.product_id.id); // set some discount
            expectGeneralPropertiesForOrder(order, true);
        }

        for (const line of order.lines) {
            line.setQuantity(5, false);
            expectGeneralPropertiesForOrder(order, true);
        }
    });

    test("[case 6] brutal pricing stress test with high qty with combo and price changes + line discount", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = getComboOrder(store);

        const productTemplateIds = [15, 5, 6, 10, 4, 14, 13, 2, 3];

        for (const tmplId of productTemplateIds) {
            const product = store.models["product.template"].get(tmplId);
            const line = await store.addLineToOrder(
                { product_tmpl_id: product, qty: tmplId },
                order
            );
            line.price_type = "manual";
            line.setUnitPrice(product.id); // set a price change
            expectGeneralPropertiesForOrder(order, true);
        }

        const bigQty = Array.from({ length: 15 }, (_, i) => i + 1);

        for (const qty of bigQty) {
            for (const line of order.lines) {
                if (line.combo_parent_id) {
                    continue;
                }
                line.setQuantity(qty, false);
                store.setDiscountFromUI(line, line.product_id.id); // set some discount
                expectGeneralPropertiesForOrder(order, true);
            }
        }

        const randomQty = [3, 27, 6, 33, 17, 3];

        for (const qty of randomQty) {
            for (const line of order.lines) {
                if (!line.combo_parent_id) {
                    line.setQuantity(qty, false);
                }
                expectGeneralPropertiesForOrder(order, true);
            }
        }
    });

    test("[case 7] global discount", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = store.addNewOrder();

        const productTemplateIds = [15, 5, 6, 10, 4, 14, 13, 2, 3];

        for (const tmplId of productTemplateIds) {
            const product = store.models["product.template"].get(tmplId);
            await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
            expectGeneralPropertiesForOrder(order);
        }

        store.applyDiscount(10, order); // apply global discount of 10%

        // Change quantities, discount should be adapted in price changes
        for (const line of order.lines) {
            line.setQuantity(line.product_id.id, false);
            expectGeneralPropertiesForOrder(order, true);
        }
    });

    test("[case 8] price change + global discount", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = store.addNewOrder();

        const productTemplateIds = [15, 5, 6, 10, 4, 14, 13, 2, 3];

        for (const tmplId of productTemplateIds) {
            const product = store.models["product.template"].get(tmplId);

            const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
            line.price_type = "manual";
            line.setUnitPrice(product.id); // set a price change
            expectGeneralPropertiesForOrder(order, true);
        }

        store.applyDiscount(10, order); // apply global discount of 10%

        // Change quantities, discount should be adapted in price changes
        for (const line of order.lines) {
            line.setQuantity(line.product_id.id, false);
            expectGeneralPropertiesForOrder(order, true);
        }
    });

    test("[case 9] combo + global discount", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = getComboOrder(store);

        const productTemplateIds = [15, 5, 6, 10, 4, 14, 13, 2, 3];

        for (const tmplId of productTemplateIds) {
            const product = store.models["product.template"].get(tmplId);
            await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
            expectGeneralPropertiesForOrder(order);
        }

        store.applyDiscount(10, order); // apply global discount of 10%

        // Change quantities, discount should be adapted in price changes
        for (const line of order.lines) {
            if (line.combo_parent_id) {
                continue;
            }
            line.setQuantity(line.product_id.id, false);
            expectGeneralPropertiesForOrder(order, true);
        }
    });

    test("[case 10] combo + price change + global discount", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = getComboOrder(store);

        const productTemplateIds = [15, 5, 6, 10, 4, 14, 13, 2, 3];

        for (const tmplId of productTemplateIds) {
            const product = store.models["product.template"].get(tmplId);

            const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
            line.price_type = "manual";
            line.setUnitPrice(product.id); // set a price change
            expectGeneralPropertiesForOrder(order, true);
        }

        store.applyDiscount(10, order); // apply global discount of 10%

        // Change quantities, discount should be adapted in price changes
        for (const line of order.lines) {
            if (line.combo_parent_id) {
                continue;
            }
            line.setQuantity(line.product_id.id, false);
            expectGeneralPropertiesForOrder(order, true);
        }
    });

    test("[case 11] pricelist", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = store.addNewOrder();

        const productTemplateIds = [15, 5, 6, 10, 4, 14, 13, 2, 3];

        for (const tmplId of productTemplateIds) {
            const product = store.models["product.template"].get(tmplId);
            await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
            expectGeneralPropertiesForOrder(order);
        }

        store.selectPricelist(order.config.available_pricelist_ids[0]);

        // Change quantities, pricelist should be applied in price changes
        for (const line of order.lines) {
            line.setQuantity(line.product_id.id, false);
            expectGeneralPropertiesForOrder(order, true);
        }
    });

    test("[case 12] combo + pricelist", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = getComboOrder(store);

        const productTemplateIds = [15, 5, 6, 10, 4, 14, 13, 2, 3];

        for (const tmplId of productTemplateIds) {
            const product = store.models["product.template"].get(tmplId);
            await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
            expectGeneralPropertiesForOrder(order);
        }

        store.selectPricelist(order.config.available_pricelist_ids[0]);

        // Change quantities, pricelist should be applied in price changes
        for (const line of order.lines) {
            if (line.combo_parent_id) {
                continue;
            }
            line.setQuantity(line.product_id.id, false);
            expectGeneralPropertiesForOrder(order, true);
        }
    });

    test("[case 13] fiscal position", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = getComboOrder(store);

        const productTemplateIds = [15, 5, 6, 10, 4, 14, 13, 2, 3];

        for (const tmplId of productTemplateIds) {
            const product = store.models["product.template"].get(tmplId);
            await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
            expectGeneralPropertiesForOrder(order);
        }

        order.fiscal_position_id = store.models["account.fiscal.position"].get(1);

        for (const line of order.lines) {
            if (line.combo_parent_id) {
                continue;
            }
            line.setQuantity(line.product_id.id, false);
            expectGeneralPropertiesForOrder(order);
        }
    });

    test("[case 14] combo + price change + line discount + global discount + pricelist", async () => {
        const store = await setupPosEnv({ setupCashier: false });
        const order = getComboOrder(store);

        const productTemplateIds = [15, 5, 6, 10, 4, 14, 13, 2, 3];

        for (const tmplId of productTemplateIds) {
            const product = store.models["product.template"].get(tmplId);
            const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
            line.price_type = "manual";
            line.setUnitPrice(product.id); // set a price change
            expectGeneralPropertiesForOrder(order, true);
        }

        for (const line of order.lines) {
            if (line.combo_parent_id) {
                continue;
            }
            line.setQuantity(line.product_id.id + 5, false);
            store.setDiscountFromUI(line, line.product_id.id + 10); // set some discount
            expectGeneralPropertiesForOrder(order, true);
        }

        store.applyDiscount(15, order); // apply global discount of 15%
        expectGeneralPropertiesForOrder(order, true);
        store.selectPricelist(order.config.available_pricelist_ids[0]);
        expectGeneralPropertiesForOrder(order, true);

        for (const line of order.lines) {
            if (line.combo_parent_id) {
                continue;
            }
            line.setQuantity(line.qty - 2, false);
            expectGeneralPropertiesForOrder(order, true);
        }
    });
    //FIXME: test with products that have extra price
    //FIXME: test with product combo where subLine qty > qty included
});
