# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.tests import TransactionCase

ORDER_ID_MOCK = 123456789

# Mock data for buyer address

BUYER_ADDRESS_MOCK = {
    'first_name': 'Gederic',
    'last_name': 'Frilson',
    'phone': '+1 234-567-8910',
    'address1': '123 RainBowMan Street',
    'address2': 'Apartment 4B',
    'address3': '',  # Used as state/region
    'city': 'New Duck City',
    'post_code': '12345',
    'country': 'VN',
}

ORDER_ITEM_MOCK = {
    'order_id': ORDER_ID_MOCK,
    'name': 'Test Product',
    'item_price': 100.0,
    'tax_amount': 0.0,
    'status': 'pending',
    'paid_price': 80.0,
    'sku': 'TEST-SKU-001',
    'sku_id': '10001',
    'order_item_id': 90001,
    'currency': 'VND',
    'buyer_id': 30001,
    'shipping_provider_type': 'standard',
    'shipment_provider': '',
    'updated_at': '2020-01-15 00:00:00 +0000',
    'is_fbl': 0,
    'package_id': '',
    'tracking_code': '',
}

ORDER_MOCK = {
    'order_id': ORDER_ID_MOCK,
    'created_at': '2020-01-15 00:00:00 +0000',
    'updated_at': '2020-01-15 00:00:00 +0000',
    'address_billing': BUYER_ADDRESS_MOCK,
    'address_shipping': BUYER_ADDRESS_MOCK,
    'customer_last_name': 'Frilson',
    'customer_first_name': 'Gederic',
    'shipping_fee': 10.0,
    'payment_method': 'COD',
    'statuses': ['pending'],
    'price': '170.0',
    'items_count': 1,
    'voucher': 10.0,
    'voucher_platform': 5.0,
    'voucher_seller': 5.0,
    'order_number': ORDER_ID_MOCK,
}

AUTH_RESPONSE_MOCK = {
    'code': '0',
    'request_id': '0001',
    'access_token': 'ACCESS_TOKEN_123',
    'refresh_token': 'REFRESH_TOKEN_123',
    'expires_in': 14400,  # 4 days
    'refresh_expires_in': 30 * 24 * 3600,  # 30 days
}

REFRESH_TOKEN_RESPONSE_MOCK = {**AUTH_RESPONSE_MOCK}

GET_SELLER_RESPONSE_MOCK = {
    'code': '0',
    'request_id': '0001',
    'data': {'name': 'mock_lazada_shop', 'seller_id': 1, 'status': 'ACTIVE'},
}

GET_ORDERS_RESPONSE_MOCK = {
    'code': '0',
    'request_id': '0001',
    'data': {'countTotal': 1, 'count': 1, 'orders': [ORDER_MOCK]},
}

GET_ORDER_ITEMS_RESPONSE_MOCK = {
    'code': '0',
    'request_id': '0001',
    'data': [
        {'order_id': ORDER_ID_MOCK, 'order_number': ORDER_ID_MOCK, 'order_items': [ORDER_ITEM_MOCK]}
    ],
}

GET_ORDER_RESPONSE_MOCK = {'code': '0', 'request_id': '0001', 'data': ORDER_MOCK}

GET_PRODUCTS_RESPONSE_MOCK = {
    'code': '0',
    'request_id': '0001',
    'data': {
        'total_products': 1,
        'products': [
            {
                'item_id': 1111111111,
                'status': 'Active',
                'skus': [
                    {
                        'SellerSku': ORDER_ITEM_MOCK['sku'],
                        'Status': 'active',
                        'SkuId': int(ORDER_ITEM_MOCK['sku_id']),
                        'fblWarehouseInventories': [],
                    }
                ],
            }
        ],
    },
}

UPDATE_STOCK_RESPONSE_MOCK = {'code': '0', 'request_id': '0001'}

GET_SHIPMENT_PROVIDER_RESPONSE_MOCK = {
    'code': '0',
    'request_id': '0001',
    'result': {
        'success': True,
        'data': {
            'platform_default': 1,
            'shipment_providers': [{'name': 'warehouse_name', 'provider_code': 'A'}],
            'shipping_allocate_type': 'NTFS',
        },
    },
}

SET_RTS_RESPONSE_MOCK = {'code': '0', 'request_id': '0001', 'result': {'success': True}}

PRINT_AWB_RESPONSE_MOCK = {
    'code': '0',
    'request_id': '0001',
    'result': {'success': True, 'data': {'pdf_url': 'https://lazada.com/lazada-label.pdf'}},
}

PACKAGE_PACK_RESPONSE_MOCK = {
    'code': '0',
    'request_id': '0001',
    'result': {
        'success': True,
        'data': {
            'pack_order_list': [
                {
                    'order_item_list': [
                        {
                            'order_item_id': ORDER_ITEM_MOCK['order_item_id'],
                            'item_err_code': '0',
                            'package_id': 'PACK-001',
                            'tracking_number': 'TRACK-001',
                        }
                    ]
                }
            ]
        },
    },
}

# Map of API operations to their corresponding response data
OPERATIONS_RESPONSES_MAP = {
    'RefreshAccessToken': REFRESH_TOKEN_RESPONSE_MOCK,
    'GetSeller': GET_SELLER_RESPONSE_MOCK,
    'GetOrders': GET_ORDERS_RESPONSE_MOCK,
    'GetMultipleOrderItems': GET_ORDER_ITEMS_RESPONSE_MOCK,
    'GetOrder': GET_ORDER_RESPONSE_MOCK,
    'GetProducts': GET_PRODUCTS_RESPONSE_MOCK,
    'UpdateSellableQuantity': UPDATE_STOCK_RESPONSE_MOCK,
    'GetShipmentProvider': GET_SHIPMENT_PROVIDER_RESPONSE_MOCK,
    'SetReadyToShip': SET_RTS_RESPONSE_MOCK,
    'PrintAWB': PRINT_AWB_RESPONSE_MOCK,
    'PackagePack': PACKAGE_PACK_RESPONSE_MOCK,
}


# Test class for common Lazada-related functionality
class TestLazadaCommon(TransactionCase):
    def setUp(self):
        super().setUp()
        self.initial_sync_date = datetime(2020, 1, 1)

        self.shop = self.env['lazada.shop'].create({
            'name': "mock_lazada_shop",
            'company_id': self.env.company.id,
            'country_id': self.env.ref('base.vn').id,
            'app_key': '1',
            'app_secret': 'test_app_secret',
            'shop_extern_id': '50001',
            'access_token': 'test_access_token',
            'access_token_expiration_date': fields.Datetime.now() + timedelta(hours=4),
            'refresh_token': 'test_refresh_token',
            'refresh_token_expiration_date': fields.Datetime.now() + timedelta(days=30),
            'last_orders_sync_date': self.initial_sync_date,
            'last_product_catalog_sync_date': self.initial_sync_date,
        })

        self.product = self.env['product.product'].create({
            'name': "Test Product",
            'type': 'consu',
            'default_code': ORDER_ITEM_MOCK['sku'],
            'list_price': 100.0,
            'is_storable': True,
            'tracking': 'none',
            'taxes_id': [],
        })

        self.item = self.env['lazada.item'].create({
            'product_id': self.product.id,
            'shop_id': self.shop.id,
            'lazada_item_extern_id': ORDER_ITEM_MOCK['sku_id'],
            'lazada_sku': ORDER_ITEM_MOCK['sku'],
            'sync_lazada_inventory': True,
        })

        self.partner = self.env['res.partner'].create({'name': "Test Partner"})
