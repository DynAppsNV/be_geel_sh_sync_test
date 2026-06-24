import { test, expect, describe } from "@odoo/hoot";
import {
    expectTransactionLine,
    setupPosBlackboxEnv,
    expectGeneralProperties,
    expectCostCenter,
    expectFinancial,
    generatePosOrder,
} from "@l10n_be_pos_blackbox/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { patchWithCleanup, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { PosBlackboxBe } from "@l10n_be_pos_blackbox/common/blackbox/blackbox";

definePosModels();

describe("sign_sale with customer account", () => {
    patchWithCleanup(ConfirmationDialog.prototype, {
        setup() {
            super.setup();
            this.props.confirm();
        },
    });
    patchWithCleanup(PosBlackboxBe.prototype, {
        async ping() {
            return true;
        },
    });

    test("signSale paying with customer account", async () => {
        const store = await setupPosBlackboxEnv();
        const models = store.models;
        const martini = models["product.product"].find((p) => p.name === "Dry Martini");
        const burger = models["product.product"].find((p) => p.name === "Burger of the Chef");
        const order = generatePosOrder(models, [
            {
                product_id: martini.id,
                qty: 2,
                price_unit: martini.lst_price,
                tax_ids: martini.taxes_id.map((t) => t.id),
            },
            {
                product_id: burger.id,
                qty: 1,
                price_unit: burger.lst_price,
                tax_ids: burger.taxes_id.map((t) => t.id),
            },
        ]);
        const partner = models["res.partner"].get(8);
        const payLaterMethod = models["pos.payment.method"].get(3);

        order.setPartner(partner);

        // Pay order with customer account
        order.state = "paid";
        store.models["pos.payment"].create({
            amount: order.priceIncl,
            pos_order_id: order,
            payment_method_id: payLaterMethod,
        });
        store.addPendingOrder([order.id]);

        const response = await store.blackbox.signSale.sign(order, "1234567890");
        const input = response.formatted;
        const transactions = input.transaction.transactionLines;
        const financials = input.financials;

        expectGeneralProperties(input, { order: order, ticketMedium: "DIGITAL" });

        expect(transactions).toHaveLength(2);
        expect(financials).toHaveLength(1);

        expectCostCenter(
            input.costCenter,
            partner.id.toString() + " " + partner.name,
            "CUSTOMER",
            partner.vat
        );

        expectFinancial(
            financials[0],
            payLaterMethod.name,
            "PAYMENT",
            order.priceIncl,
            "CUSTOMER_CREDIT"
        );
    });

    test("signSale settling due", async () => {
        const store = await setupPosBlackboxEnv();
        const models = store.models;

        const order = store.addNewOrder();
        const partner = models["res.partner"].get(8);

        const settleDueProduct = models["product.product"].get(206);
        const cashPaymentMethod = models["pos.payment.method"].get(2);
        const payLaterMethod = models["pos.payment.method"].get(3);

        await store.addLineToCurrentOrder({
            price_unit: 100,
            qty: 1,
            taxes_id: [],
            product_tmpl_id: settleDueProduct,
        });
        order.commercialPartnerId = partner.id;
        order.setPartner(partner);

        const paymentLine = order.addPaymentline(cashPaymentMethod);
        paymentLine.data.amount = 100;

        const screen = await mountWithCleanup(PaymentScreen, {
            props: { orderUuid: order.uuid },
        });

        await screen.validateOrder();

        const cashPaymentLine = order.payment_ids.find(
            (p) => p.payment_method_id.id === cashPaymentMethod.id
        );
        const payLaterPaymentLine = order.payment_ids.find(
            (p) => p.payment_method_id.id === payLaterMethod.id
        );

        expect(cashPaymentLine.amount).toBe(100);
        expect(payLaterPaymentLine.amount).toBe(-100);

        partner.vat = "BE0246697724";
        partner.name = "Test Customer";
        const response = await store.blackbox.signSale.sign(order, "1234567890");
        const input = response.formatted;
        const transactions = input.transaction.transactionLines;
        const financials = input.financials;

        expectGeneralProperties(input, { order: order, orderPrice: 100, ticketMedium: "DIGITAL" });

        expect(transactions).toHaveLength(1);
        expect(financials).toHaveLength(1);

        expectCostCenter(
            input.costCenter,
            partner.id.toString() + " " + partner.name,
            "CUSTOMER",
            partner.vat
        );
        expectFinancial(financials[0], cashPaymentMethod.name, "PAYMENT", 100, "CASH");
        expectTransactionLine(
            transactions[0],
            settleDueProduct,
            1,
            "PIECE",
            100,
            "X",
            "SINGLE_PRODUCT"
        );
    });
});
