import { test, expect } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, expectFormattedPrice } from "@point_of_sale/../tests/unit/utils";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

definePosModels();

test("fastValidate", async () => {
    patchWithCleanup(ConfirmationDialog.prototype, {
        setup() {
            super.setup();
            this.props.confirm();
        },
    });

    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const partner = store.models["res.partner"].get(5);
    order.setPartner(partner);
    order.commercialPartnerId = order.partner_id.commercial_partner_id.id;

    const productScreen = await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });
    await productScreen.addProductToOrder(order.config.settle_invoice_product_id);

    expect(order.displayPrice).toBe(3);
    expectFormattedPrice(productScreen.total, "$ 3.00");
    expect(productScreen.items).toBe("1");

    const fastPaymentMethod = order.config.fast_payment_method_ids[0];
    await productScreen.fastValidate(fastPaymentMethod);

    const [fastPaymentLine, payLaterPaymentLine] = order.payment_ids;

    expect(fastPaymentLine.amount).toBe(3);
    expect(payLaterPaymentLine.amount).toBe(-3);
});
