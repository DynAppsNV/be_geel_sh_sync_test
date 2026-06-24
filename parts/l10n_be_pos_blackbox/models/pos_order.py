from odoo import models, fields


class PosOrder(models.Model):
    _inherit = "pos.order"

    # FDM Signature fields (Normal event)
    l10n_be_fdm_id = fields.Char(string="FDM ID", readonly=True)
    l10n_be_fdm_date_time = fields.Datetime(string="FDM Date Time", readonly=True)
    l10n_be_pos_id = fields.Char(string="POS ID", readonly=True)
    l10n_be_terminal_id = fields.Char(string="Terminal ID", readonly=True)
    l10n_be_device_id = fields.Char(string="Device ID", readonly=True)
    l10n_be_pos_date_time = fields.Datetime(string="POS Date Time", readonly=True)
    l10n_be_event_label = fields.Char(string="Event Label", readonly=True)
    l10n_be_event_counter = fields.Integer(string="Event Counter", readonly=True)
    l10n_be_total_counter = fields.Integer(string="Total Counter", readonly=True)
    l10n_be_short_signature = fields.Char(string="Short Signature", readonly=True)
    l10n_be_verification_url = fields.Char(string="Verification URL", readonly=True)
    l10n_be_vat_calc = fields.Json(string="VAT Calculation", readonly=True)
    l10n_be_footer = fields.Json(string="VAT receipt footer", readonly=True)
    # FDM Signature fields (Invoice event)
    l10n_be_I_total_counter = fields.Integer(string="I Total Counter", readonly=True)
    l10n_be_I_event_counter = fields.Integer(string="I Event Counter", readonly=True)
    l10n_be_I_event_label = fields.Char(string="I Event Label", readonly=True)
    l10n_be_I_fdm_date_time = fields.Datetime(string="I FDM Date Time", readonly=True)
    l10n_be_I_fdm_id = fields.Char(string="I FDM ID", readonly=True)
    l10n_be_last_transaction_by_line = fields.Json(string="Last Transaction By Line uuid", readonly=True)
    """
    Details of "l10n_be_last_transaction_by_line"
    ---------------------------------------------
    Stores a snapshot of the last successfully signed transaction state, keyed by
    order line UUID. It is used to compute the **delta** between the current order
    state and the previously signed state, so that only the necessary corrections
    (new, modified, or deleted lines) are sent to the Belgian Blackbox FDM device.

    Structure::

        {
            "<line_uuid>": {
                "transLine": {
                    # Full TransactionLineInput payload as sent to the FDM
                    "lineType": "SINGLE_PRODUCT" | "COMPOSITE_PRODUCT",
                    "mainProduct": { ... },
                    "subProducts": [ ... ],   # only for COMPOSITE_PRODUCT
                    "lineTotal": float,
                },
                "lineInfos": {
                    # Snapshot of the pricing state at the time of the last sign
                    "priceUnit": float,      # unit price before discount
                    "discount":  float,      # per-line discount percentage
                    "globalDiscount": float, # order-level global discount percentage
                    "qty": float,            # signed quantity (0 means already corrected)
                },
            },
            ...
        }

    Usage:
        Read during ``generateSignOrderInput()`` and ``generateSignCanceledOrderInput()``
        to determine which lines are new, modified (price/quantity change), or deleted
        since the previous sign call.

        Written (via ``order.uiState.transactionLinesMap``) after each successful
        ``generateSignOrderInput()`` call, so it always reflects the last committed
        FDM state.

        - **New line** (UUID absent from this field): sent as-is.
        - **Modified line** (UUID present but payload differs): a CORRECTION or
        PRICE_CHANGE negation line is emitted first, followed by the updated line.
        - **Deleted line** (UUID present here but absent from current order): a
        CORRECTION negation line is emitted.
        - **Cancel order**: all entries with ``lineInfos.qty != 0`` are negated and
        sent as CORRECTION lines.
    """
    l10n_be_grouping_id = fields.Json(string="Grouping ID by line uuid", readonly=True)
    """
    Details of "l10n_be_grouping_id"
    --------------------------------
    Persists the monotonically-incrementing ``groupingId`` counter and the
    per-line grouping-ID assignments across multiple ``signOrder`` calls on the
    same order. The Blackbox FDM uses ``groupingId`` values to associate related
    price-change entries (e.g. all DISCOUNT lines for the same product) with each
    other across separate sign requests.

    Structure::

        {
            "groupingIdCount": int,          # global counter; incremented by _nextGroupingId()
            "globalDiscountGId": int | None, # shared groupingId for ORDER-scope discount entries
            "roundingAdaptationGId": int | None, # shared groupingId for ROUNDING_ADAPTATION entries
            "lines": {
                "<line_uuid>": {
                    "unitPriceChangeGId": int | None,  # groupingId for UNIT_PRICE_CHANGE entries
                    "menuDiscountGId":    int | None,  # groupingId for MENU_DISCOUNT entries
                    "discountGId":        int | None,  # groupingId for DISCOUNT_* entries
                },
                ...
            }
        }

    Usage:
        - Lazily initialised on first access via ``_getGroupingState()``.
        - ``_nextGroupingId()`` atomically increments ``groupingIdCount`` and returns
        the new value so each new group gets a unique, stable identifier.
        - When a line's pricing attributes change between sign calls
        (price-unit, per-line discount, or global discount), the relevant slot
        (``unitPriceChangeGId``, ``menuDiscountGId``, ``discountGId``) is reset to
        ``None``, which forces a fresh ``groupingId`` to be allocated for
        the corrected entries — ensuring the FDM can distinguish the new price-change group
        from the previously reported one.
        - Because this field is stored on the order record (readonly from the UI),
        the counter and assignments survive page reloads and re-opens of the same
        order.
    """
    old_pos_blackbox_be_data = fields.Json(string="Old POS Blackbox BE Data", readonly=True, copy=False)

    def _get_cashier(self):
        self.ensure_one()
        return self.user_id
