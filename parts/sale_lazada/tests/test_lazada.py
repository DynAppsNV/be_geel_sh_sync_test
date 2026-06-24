# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import freeze_time, tagged
from odoo.tools import mute_logger

from odoo.addons.sale_lazada import const
from odoo.addons.sale_lazada import utils as lazada_utils
from odoo.addons.sale_lazada.tests import common


@tagged('post_install', '-at_install')
@freeze_time('2020-02-01')
class TestLazada(common.TestLazadaCommon):
    @mute_logger('odoo.addons.sale_lazada.models.lazada_shop')
    def test_sync_orders_full(self):
        """
        Test the orders synchronization with on-the-fly creation of all required records.

        An order with a product line is created.
        """
        with (
            patch(
                'odoo.addons.sale_lazada.utils.make_lazada_api_request',
                new=lambda operation, _shop, *_args, **_kwargs: (
                    common.OPERATIONS_RESPONSES_MAP[operation]
                ),
            ),
            patch(
                'odoo.addons.sale_lazada.models.lazada_shop.LazadaShop._compute_subtotal',
                new=lambda _self, subtotal_, *_args, **_kwargs: subtotal_,
            ),
        ):
            self.shop._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('lazada_order_ref', '=', common.ORDER_ID_MOCK)])
            product_line = order.order_line.filtered(
                lambda line: line.product_id.default_code == 'TEST-SKU-001'
            )

            self.assertEqual(
                self.shop.last_orders_sync_date,
                fields.Datetime.now(),
                msg="The last_orders_sync_date should be equal to current datetime after a"
                " successful run",
            )
            self.assertEqual(len(order), 1, msg="An order should be created")
            self.assertRecordValues(
                order,
                [
                    {
                        'date_order': datetime(2020, 1, 15),
                        'company_id': self.shop.company_id.id,
                        'user_id': self.shop.user_id.id,
                        'team_id': self.shop.team_id.id,
                        'lazada_fulfillment_type': 'fbm',
                    }
                ],
            )
            self.assertRecordValues(
                product_line,
                [
                    {
                        'price_unit': 100.0,
                        'discount': 20.0,
                        'product_uom_qty': 1.0,
                        'product_id': self.product.id,
                    }
                ],
            )

    @mute_logger('odoo.addons.sale_lazada.models.lazada_shop')
    def test_sync_orders_partial(self):
        """
        Test the orders synchronization interruption with API throttling.

        Two orders are available in the response. The first one is fully synchronized, the second
        one is throttled.
        """

        def get_lazada_api_response_mock(operation_, _shop, *_args, **_kwargs):
            """
            Return a mocked response without making an actual call to the Lazada API.
            Raise a LazadaRateLimitError when the second order is synchronized,
            to simulate a throttling issue.
            """
            if operation_ == 'GetOrders':
                self.api_call_count += 1
                if self.api_call_count == 2:
                    raise lazada_utils.LazadaRateLimitError(operation_)
                return common.GET_ORDERS_RESPONSE_MOCK
            return common.OPERATIONS_RESPONSES_MAP[operation_]

        with patch(
            'odoo.addons.sale_lazada.utils.make_lazada_api_request',
            new=get_lazada_api_response_mock,
        ):
            self.api_call_count = 0

            self.shop._sync_orders(auto_commit=False)

            orders = self.env['sale.order'].search([
                ('lazada_order_ref', '=', str(common.ORDER_ID_MOCK))
            ])
            self.assertEqual(len(orders), 1, msg="Only one order should be synchronized")
            self.assertEqual(
                self.shop.last_orders_sync_date,
                self.initial_sync_date + timedelta(days=const.ORDER_LIST_DAYS_LIMIT),
                msg="The last_orders_sync_date should be equal to the LastUpdateDate of the last"
                " fully synchronized period.",
            )
            self.assertEqual(self.api_call_count, 2)

    @mute_logger('odoo.addons.sale_lazada.models.lazada_shop')
    def test_sync_orders_fail(self):
        """
        Test the orders synchronization cancellation with API throttling.

        The last order synchronization date should not be updated if the rate limit of one operation
        was reached.
        """

        def get_lazada_api_response_mock(operation_, _shop, *_args, **_kwargs):
            """Return a mocked response or raise a LazadaRateLimitError without making an actual
            call to the Lazada API."""
            self.api_call_count += 1
            if operation_ == 'GetOrders':
                raise lazada_utils.LazadaRateLimitError(operation_)
            return common.OPERATIONS_RESPONSES_MAP[operation_]

        with patch(
            'odoo.addons.sale_lazada.utils.make_lazada_api_request',
            new=get_lazada_api_response_mock,
        ):
            self.api_call_count = 0
            last_orders_sync_date_copy = self.shop.last_orders_sync_date

            self.shop._sync_orders(auto_commit=False)

            self.assertEqual(self.api_call_count, 1)
            self.assertEqual(self.shop.last_orders_sync_date, last_orders_sync_date_copy)

    @mute_logger('odoo.addons.sale_lazada.models.lazada_shop')
    def test_sync_orders_no_active_shop(self):
        """
        Test the orders synchronization cancellation with no active shop.

        No order synchronization should be performed as the shop is inactive.
        """

        def get_lazada_api_response_mock(operation_, _shop, *_args, **_kwargs):
            self.api_call_count += 1
            return common.OPERATIONS_RESPONSES_MAP[operation_]

        with patch(
            'odoo.addons.sale_lazada.utils.make_lazada_api_request',
            new=get_lazada_api_response_mock,
        ):
            self.api_call_count = 0
            last_orders_sync_date_copy = self.shop.last_orders_sync_date
            self.shop.write({'active': False})

            self.env['lazada.shop']._sync_orders(auto_commit=False)

            self.assertEqual(self.api_call_count, 0)
            self.assertEqual(self.shop.last_orders_sync_date, last_orders_sync_date_copy)

    @mute_logger('odoo.addons.sale_lazada.models.lazada_shop')
    def test_sync_orders_fbl(self):
        """Test the orders synchronization with fulfillment type 'Fulfillment By Lazada'.

        An order with a product line is created.
        FBL order should generate a stock move for each product and use the FBL location.
        """

        def get_lazada_api_response_mock(operation_, _shop, *_args, **_kwargs):
            """Return a mocked response with a confirmed order with FBL fulfillment type."""
            if operation_ == 'GetOrders':
                return {
                    **common.GET_ORDERS_RESPONSE_MOCK,
                    'data': {'orders': [{**common.ORDER_MOCK, 'statuses': ['confirmed']}]},
                }
            if operation_ == 'GetMultipleOrderItems':
                return {
                    **common.GET_ORDER_ITEMS_RESPONSE_MOCK,
                    'data': [
                        {
                            'order_id': common.ORDER_ID_MOCK,
                            'order_number': common.ORDER_ID_MOCK,
                            'order_items': [
                                {**common.ORDER_ITEM_MOCK, 'is_fbl': 1, 'status': 'confirmed'}
                            ],
                        }
                    ],
                }
            return common.OPERATIONS_RESPONSES_MAP[operation_]

        with patch(
            'odoo.addons.sale_lazada.utils.make_lazada_api_request',
            new=get_lazada_api_response_mock,
        ):
            self.shop._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('lazada_order_ref', '=', common.ORDER_ID_MOCK)])

            self.assertEqual(len(order), 1)
            self.assertEqual(order.lazada_fulfillment_type, 'fbl')
            self.assertEqual(len(order.order_line), 1)
            self.assertEqual(
                order.warehouse_id,
                self.shop.fbl_location_id.warehouse_id,
                "FBL orders should use the FBL location's warehouse",
            )

    @mute_logger('odoo.addons.sale_lazada.models.lazada_shop')
    def test_sync_orders_cancel(self):
        """
        Test the cancellation synchronization of a Lazada order.

        The order is first imported, then Lazada reports a cancellation that should cancel
        the related sale order and mark the order items as canceled.
        """

        def get_lazada_api_response(operation_, _shop, _params=None, **_kwargs):
            if operation_ == 'GetOrders':
                statuses = ['pending'] if not self.order_canceled else ['canceled']
                return {
                    'code': '0',
                    'request_id': '0_sync_orders_cancel',
                    'data': {
                        'countTotal': 1,
                        'count': 1,
                        'orders': [{**common.ORDER_MOCK, 'statuses': statuses}],
                    },
                }
            if operation_ == 'GetMultipleOrderItems':
                status = 'pending' if not self.order_canceled else 'canceled'
                return {
                    'code': '0',
                    'request_id': '0_sync_orders_cancel_items',
                    'data': [
                        {
                            'order_id': common.ORDER_ID_MOCK,
                            'order_number': common.ORDER_ID_MOCK,
                            'order_items': [{**common.ORDER_ITEM_MOCK, 'status': status}],
                        }
                    ],
                }
            return common.OPERATIONS_RESPONSES_MAP[operation_]

        with (
            patch(
                'odoo.addons.sale_lazada.utils.make_lazada_api_request', new=get_lazada_api_response
            ),
            patch(
                'odoo.addons.sale_lazada.models.lazada_shop.LazadaShop._compute_subtotal',
                new=lambda _self, subtotal_, *_args, **_kwargs: subtotal_,
            ),
        ):
            self.order_canceled = False

            self.shop._sync_orders(auto_commit=False)

            order = self.env['sale.order'].search([
                ('lazada_order_ref', '=', common.ORDER_MOCK['order_id'])
            ])
            self.assertEqual(len(order), 1, "Order should be created before cancellation.")
            self.order_canceled = True

            with freeze_time('2020-03-01'):
                self.shop._sync_orders(auto_commit=False)

            self.assertEqual(order.state, 'cancel', "Canceled orders should be canceled in Odoo.")
            self.assertEqual(
                order.picking_ids.move_ids[0].product_uom_qty,
                0,
                "The product quantity should be 0 after cancellation.",
            )
            self.assertTrue(
                all(item.status == 'canceled' for item in order.order_line.lazada_order_item_ids),
                "All Lazada order items should be marked as canceled.",
            )

    @mute_logger('odoo.addons.sale_lazada.models.lazada_shop')
    def test_sync_inventory(self):
        """
        Test the inventory synchronization to Lazada.

        Verifies that product stock quantities are correctly sent to Lazada API
        when synchronization is enabled.
        """

        def get_lazada_api_response_mock(operation_, _shop, params={}, **_kwargs):
            """Return a mocked response for inventory updates."""
            if operation_ == 'UpdateSellableQuantity':
                self.payload = json.loads(params['payload'])
            return common.OPERATIONS_RESPONSES_MAP[operation_]

        with patch(
            'odoo.addons.sale_lazada.utils.make_lazada_api_request',
            new=get_lazada_api_response_mock,
        ):
            self.shop.synchronize_inventory = True
            # Update the stock level of the product
            self.env['stock.quant']._update_available_quantity(
                self.product, self.shop.fbm_warehouse_id.lot_stock_id, 100
            )

            self.shop._sync_inventory(auto_commit=False)

            item_payload = self.payload['Request']['Product']['Skus']['Sku'][0]
            self.assertEqual(item_payload['SkuId'], str(common.ORDER_ITEM_MOCK['sku_id']))
            self.assertEqual(item_payload['SellableQuantity'], 100)

    @mute_logger('odoo.addons.sale_lazada.models.lazada_shop')
    def test_sync_inventory_is_skipped_when_disabled(self):
        """Test that inventory synchronization is skipped when disabled for the shop."""

        def get_lazada_api_response_mock(operation_, _shop, *_args, **_kwargs):
            """Inventory update should not be called."""
            self.api_call_count += 1
            return common.OPERATIONS_RESPONSES_MAP[operation_]

        with patch(
            'odoo.addons.sale_lazada.utils.make_lazada_api_request',
            new=get_lazada_api_response_mock,
        ):
            self.api_call_count = 0
            self.shop.synchronize_inventory = False
            self.shop._sync_inventory(auto_commit=False)
            self.assertEqual(self.api_call_count, 0)

    @mute_logger('odoo.addons.sale_lazada.models.lazada_shop')
    def test_sync_product_catalog_initialization(self):
        """
        Test the product catalog synchronization from Lazada.

        It will be initialized if the shop has no Lazada items.
        """

        def get_lazada_api_response_mock(operation_, _shop, params_=None, *_args, **_kwargs):
            """Return a mocked response for product catalog."""
            params_ = params_ or {}
            if operation_ == 'GetProducts':
                self.time_from = params_.get('update_after')
                self.time_to = params_.get('update_before')
            return common.OPERATIONS_RESPONSES_MAP[operation_]

        with patch(
            'odoo.addons.sale_lazada.utils.make_lazada_api_request',
            new=get_lazada_api_response_mock,
        ):
            self.shop.last_product_catalog_sync_date = None
            self.shop.lazada_item_ids = self.env['lazada.item']
            self.assertEqual(len(self.shop.lazada_item_ids), 0)

            self.shop._sync_product_catalog()

            self.assertEqual(len(self.shop.lazada_item_ids), 1)
            self.assertEqual(
                self.shop.lazada_item_ids.lazada_item_extern_id, common.ORDER_ITEM_MOCK['sku_id']
            )
            self.assertEqual(self.shop.lazada_item_ids.product_id.default_code, 'TEST-SKU-001')
            self.assertTrue(self.shop.lazada_item_ids.sync_lazada_inventory)

            self.assertEqual(self.time_from, None)
            self.assertEqual(self.time_to, None)

            self.assertEqual(self.shop.last_product_catalog_sync_date, datetime(2020, 2, 1))

    @mute_logger('odoo.addons.sale_lazada.models.lazada_shop')
    def test_sync_product_catalog_update(self):
        """
        Test the product catalog synchronization from Lazada after the initial synchronization.

        Verifies that new products are added to the catalog and the sync date is updated
        with proper time range parameters sent to the API.
        """

        def get_lazada_api_response_mock(operation_, _shop, params={}, *_args, **_kwargs):
            """Return a mocked response of an updated product for product catalog."""
            if operation_ == 'GetProducts':
                self.time_from = params.get('update_after')
                self.time_to = params.get('update_before')
                return {
                    **common.GET_PRODUCTS_RESPONSE_MOCK,
                    'data': {
                        'total_products': 1,
                        'products': [
                            {
                                'item_id': 2222222222,
                                'status': 'Active',
                                'skus': [
                                    {
                                        'SellerSku': 'TEST-SKU-002',
                                        'Status': 'active',
                                        'SkuId': 10002,
                                        'fblWarehouseInventories': [],
                                    }
                                ],
                            }
                        ],
                    },
                }
            return common.OPERATIONS_RESPONSES_MAP[operation_]

        with patch(
            'odoo.addons.sale_lazada.utils.make_lazada_api_request',
            new=get_lazada_api_response_mock,
        ):
            # Create a storable product for the new SKU
            self.env['product.product'].create({
                'name': "Test Product 2",
                'type': 'consu',
                'default_code': 'TEST-SKU-002',
                'list_price': 100.0,
                'is_storable': True,
                'tracking': 'none',
                'taxes_id': [],
            })
            # Ensure the initial sync date is still the same as before the update
            self.assertEqual(self.shop.last_product_catalog_sync_date, self.initial_sync_date)

            self.shop._sync_product_catalog()

            self.assertEqual(len(self.shop.lazada_item_ids), 2)
            item = self.shop.lazada_item_ids.filtered(lambda i: i.lazada_item_extern_id == '10002')
            self.assertTrue(item)
            self.assertTrue(item.sync_lazada_inventory)

            self.assertEqual(self.time_from, '2020-01-01T07:00:00+07:00')
            self.assertEqual(self.time_to, '2020-02-01T07:00:00+07:00')

            updated_sync_date = lazada_utils.lazada_timestamp_to_datetime(
                '2020-02-01T07:00:00+07:00'
            )
            self.assertEqual(self.shop.last_product_catalog_sync_date, updated_sync_date)

    def test_find_matching_product(self):
        """
        Test the product matching functionality using the internal reference.

        Verifies that existing products are found by SKU and that non-existent products
        return False when fallback is disabled.
        """
        # Test match with existing internal reference
        found_product = self.shop._find_matching_product(
            'TEST-SKU-001', 'default_shipping', 'Default Shipping', 'service'
        )
        self.assertEqual(found_product.id, self.product.id)

        # Test no match with non-existing internal reference
        found_product = self.shop._find_matching_product(
            'NONEXISTENT-SKU', 'default_shipping', 'Default Shipping', 'service', fallback=False
        )
        self.assertFalse(found_product)

    def test_find_or_create_item(self):
        """
        Test the functionality to find or create a Lazada item.

        If the item already exists, it should be found and returned.
        If the item does not exist, it should be created and returned.
        """
        # Test existing item
        found_item = self.shop._find_or_create_item(
            'TEST-SKU-001', common.ORDER_ITEM_MOCK['sku_id'], 'fbm'
        )
        self.assertEqual(found_item.id, self.item.id)
        self.assertTrue(
            found_item.sync_lazada_inventory,
            "Existing FBM item with storable product should be marked for synchronization.",
        )

        # Test new item creation
        new_item = self.shop._find_or_create_item('NEW-SKU-001', 98765, 'fbm')
        self.assertNotEqual(new_item.id, self.item.id)
        self.assertFalse(
            new_item.sync_lazada_inventory,
            "Non-storable products should not be marked for synchronization.",
        )

    def test_find_or_create_partners_from_data(self):
        """
        Test the creation of partners from order data.

        Verifies that shipping and invoice partners are created with correct address
        details, country, phone, and Lazada buyer external ID from order data.
        """
        with patch(
            'odoo.addons.sale_lazada.models.lazada_shop.LazadaShop._find_matching_product',
            new=lambda _self, _sku, _default_xmlid, _default_name, _default_type, _fallback=True: (
                self.product
            ),
        ):
            order_data = dict(common.ORDER_MOCK)
            order_data['order_items'] = [common.ORDER_ITEM_MOCK]
            partner_shipping, partner_invoice = self.shop._find_or_create_partners_from_data(
                order_data
            )

            self.assertTrue(partner_shipping)
            self.assertTrue(partner_invoice)
            self.assertEqual(partner_shipping.name, "Gederic Frilson")
            self.assertEqual(partner_shipping.country_id.code, "VN")
            self.assertEqual(partner_shipping.lazada_buyer_extern_id, '30001')
            self.assertEqual(partner_shipping.street, "123 RainBowMan Street")
            self.assertEqual(partner_shipping.street2, "Apartment 4B")
            self.assertEqual(partner_shipping.zip, "12345")
            self.assertEqual(partner_shipping.city, "New Duck City")
            self.assertEqual(partner_shipping.phone, "+1 234-567-8910")

    def test_compute_lazada_order_status(self):
        """Test the computation of Lazada delivery status based on order item statuses."""
        order_data = dict(common.ORDER_MOCK)
        order_data['order_items'] = [dict(common.ORDER_ITEM_MOCK)]
        order = self.shop._create_order_from_data(order_data)

        order.order_line.lazada_order_item_ids.status = 'processing'

        self.assertEqual(order.lazada_order_status, 'processing')

        # Add another item with a different status to test the mixed statuses
        self.env['lazada.order.item'].create({
            'order_item_extern_id': 456,
            'sale_order_line_id': order.order_line.id,
            'stock_move_id': order.order_line.move_ids[0].id,
            'status': 'delivered',
        })

        self.assertEqual(order.lazada_order_status, 'manual')

    def test_get_lazada_aggregated_status_single_status(self):
        """Should return the status itself when only one status is present."""
        status = lazada_utils.get_lazada_aggregated_status(['processing'])
        self.assertEqual(status, 'processing')

    def test_get_lazada_aggregated_status_mixed_statuses(self):
        """Should return 'manual' when statuses are mixed."""
        status = lazada_utils.get_lazada_aggregated_status(['processing', 'delivered'])
        self.assertEqual(status, 'manual')

    def test_get_lazada_aggregated_status_canceled_and_other(self):
        """Should ignore canceled if other status exists, and return the other status."""
        status = lazada_utils.get_lazada_aggregated_status(['processing', 'canceled'])
        self.assertEqual(status, 'processing')

    def test_get_lazada_aggregated_status_all_canceled(self):
        """Should return 'canceled' if all statuses are canceled."""
        status = lazada_utils.get_lazada_aggregated_status(['canceled'])
        self.assertEqual(status, 'canceled')

    def test_should_create_fbm_order_with_pending_status(self):
        """FBM should create order when status is 'pending'."""
        order_data_fbm_pending = {
            'order_items': [{**common.ORDER_ITEM_MOCK, 'shipping_provider_type': 'standard'}],
            'statuses': ['pending'],
        }
        self.assertTrue(
            self.shop._should_create_order(order_data_fbm_pending, 'fbm'),
            "FBM orders with 'pending' status should be synchronized.",
        )

    def test_should_not_create_fbm_order_with_confirmed_status(self):
        """FBM should not create order when status is 'confirmed'."""
        order_data_fbm_confirmed = {
            "order_id": common.ORDER_ID_MOCK,
            'order_items': [{**common.ORDER_ITEM_MOCK, 'shipping_provider_type': 'standard'}],
            'statuses': ['confirmed'],
        }
        self.assertFalse(
            self.shop._should_create_order(order_data_fbm_confirmed, 'fbm'),
            "FBM orders without 'pending' status should be ignored.",
        )

    def test_should_create_fbl_order_with_confirmed_status(self):
        """FBL should create order when status is 'confirmed'."""
        order_data_fbl_confirmed = {
            'order_items': [
                {**common.ORDER_ITEM_MOCK, 'shipping_provider_type': 'standard', 'is_fbl': 1}
            ],
            'statuses': ['confirmed'],
        }
        self.assertTrue(
            self.shop._should_create_order(order_data_fbl_confirmed, 'fbl'),
            "FBL orders with 'confirmed' status should be synchronized.",
        )

    def test_should_not_create_fbl_order_with_pending_status(self):
        """FBL should not create order when status is 'pending'."""
        order_data_fbl_pending = {
            "order_id": common.ORDER_ID_MOCK,
            'order_items': [
                {**common.ORDER_ITEM_MOCK, 'shipping_provider_type': 'standard', 'is_fbl': 1}
            ],
            'statuses': ['pending'],
        }
        self.assertFalse(
            self.shop._should_create_order(order_data_fbl_pending, 'fbl'),
            "FBL orders without 'confirmed' status should be ignored.",
        )

    def test_get_fulfillment_type_fbm(self):
        """Ensure that a single FBM order item returns 'fbm' as fulfillment type."""
        fbm_order_data = {
            'order_id': 'TESTFBM',
            'order_items': [{**common.ORDER_ITEM_MOCK, 'is_fbl': 0}],
        }
        self.assertEqual(self.shop._get_fulfillment_type(fbm_order_data), 'fbm')

    def test_get_fulfillment_type_fbl(self):
        """Ensure that a single FBL order item returns 'fbl' as fulfillment type."""
        fbl_order_data = {
            'order_id': 'TESTFBL',
            'order_items': [{**common.ORDER_ITEM_MOCK, 'is_fbl': 1}],
        }
        self.assertEqual(self.shop._get_fulfillment_type(fbl_order_data), 'fbl')

    def test_get_fulfillment_type_mixed(self):
        """Ensure that mixed FBL and FBM order items return None (unsupported)."""
        mixed_order_data = {
            'order_id': 'TESTMIX',
            'order_items': [
                {**common.ORDER_ITEM_MOCK, 'is_fbl': 0},
                {**common.ORDER_ITEM_MOCK, 'is_fbl': 1},
            ],
        }
        self.assertIsNone(self.shop._get_fulfillment_type(mixed_order_data))
