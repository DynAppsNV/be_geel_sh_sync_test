.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
  :target: https://www.gnu.org/licenses/agpl
  :alt: License: AGPL-3

=======================================
Dynamic Approver for Purchase Approvals
=======================================

Extends the Studio approval flow for Purchase Orders with dynamic,
per-PO approver assignment and sequential step enforcement.

Key features
------------

-  **Dynamic approver assignment** — each Studio approval rule marked as
   *Dynamic Approver* resolves its actual approver at PO level via the
   *Approvers* tab, rather than using a fixed group. Available approvers
   are looked up from a company/department/approval-group matrix.
-  **Board member approval via Sign** — rules marked as *Board Approval*
   route the approval through the Sign module instead of an internal
   Odoo user. The PO PDF is rendered automatically, a signature field is
   placed on the last page, and a sign request is sent to the assigned
   board member.
-  **Sequential steps** — approval steps fire one at a time in
   *Notification Order* sequence. A step's activity or sign request is
   only created once all lower-order steps carry an approved entry,
   preventing parallel triggering.
-  **Approval matrix** — configurable per company, department (analytic
   account), and approver group. Internal users and external board
   members can both appear in the matrix. When exactly one candidate
   exists for a step, the approver is pre-filled automatically.
-  **Signature placement settings** — the position and size of the
   signature field on the PO PDF can be configured under Purchase →
   Configuration → Settings (Board Approval Signature section).
-  **Admin sign link** — administrators see a direct signing URL on
   board approval rows in the Approvers tab, allowing local testing
   without email delivery.

Files
-----

New models
~~~~~~~~~~

+----------------------+----------------------+----------------------+
| File                 | Model                | Description          |
+======================+======================+======================+
| ``models/xx_po_      | ``xx.                | Approval matrix rows |
| approval_matrix.py`` | po.approval.matrix`` | mapping company +    |
|                      |                      | department (analytic |
|                      |                      | account) + approver  |
|                      |                      | group to an internal |
|                      |                      | user or external     |
|                      |                      | board member         |
|                      |                      | partner.             |
+----------------------+----------------------+----------------------+
| ``models/xx_p        | ``x                  | Per-PO approver      |
| o_approval_user.py`` | x.po.approval.user`` | assignment lines     |
|                      |                      | (one row per dynamic |
|                      |                      | approval step).      |
|                      |                      | Tracks the assigned  |
|                      |                      | user or board member |
|                      |                      | partner and links to |
|                      |                      | the sign request for |
|                      |                      | board steps.         |
+----------------------+----------------------+----------------------+
| ``wizard             | ``xx.seed.wizard``   | Transient wizard     |
| /xx_seed_wizard.py`` |                      | that seeds demo      |
|                      |                      | departments, users,  |
|                      |                      | groups, Studio       |
|                      |                      | approval rules and   |
|                      |                      | matrix rows for      |
|                      |                      | testing.             |
+----------------------+----------------------+----------------------+

Inherited models
~~~~~~~~~~~~~~~~

+----------------------+----------------------+----------------------+
| File                 | Inherits             | What is added /      |
|                      |                      | overridden           |
+======================+======================+======================+
| ``models             | ``purchase.order``   | Adds                 |
| /purchase_order.py`` |                      | ``xx                 |
|                      |                      | _approval_line_ids`` |
|                      |                      | (O2M to              |
|                      |                      | ``xx                 |
|                      |                      | .po.approval.user``) |
|                      |                      | and                  |
|                      |                      | ``xx_department_id`` |
|                      |                      | (M2O to analytic     |
|                      |                      | account). Syncs      |
|                      |                      | approval lines on    |
|                      |                      | cr                   |
|                      |                      | eate/write/onchange. |
|                      |                      | Validates            |
|                      |                      | completeness before  |
|                      |                      | save.                |
+----------------------+----------------------+----------------------+
| ``models/studi       | ``st                 | Adds                 |
| o_approval_rule.py`` | udio.approval.rule`` | ``i                  |
|                      |                      | s_dynamic_approver`` |
|                      |                      | and                  |
|                      |                      | `                    |
|                      |                      | `is_board_approval`` |
|                      |                      | flags. Overrides     |
|                      |                      | ``_com               |
|                      |                      | pute_can_validate``, |
|                      |                      | ``check_approval``,  |
|                      |                      | ``_create_request``, |
|                      |                      | and                  |
|                      |                      | ``_set_approval`` to |
|                      |                      | enforce per-PO       |
|                      |                      | assignment and       |
|                      |                      | sequential step      |
|                      |                      | gating. Routes board |
|                      |                      | steps to Sign.       |
+----------------------+----------------------+----------------------+
| ``mode               | ``sign.request``     | Overrides ``write``  |
| ls/sign_request.py`` |                      | to detect when a     |
|                      |                      | sign request reaches |
|                      |                      | ``signed`` state and |
|                      |                      | auto-completes the   |
|                      |                      | linked board         |
|                      |                      | approval step on the |
|                      |                      | PO.                  |
+----------------------+----------------------+----------------------+
| ``models/res_        | ``r                  | Exposes four         |
| config_settings.py`` | es.config.settings`` | ``i                  |
|                      |                      | r.config_parameter`` |
|                      |                      | values               |
|                      |                      | (``b                 |
|                      |                      | oard_sign_pos_x/y``, |
|                      |                      | ``board_             |
|                      |                      | sign_width/height``) |
|                      |                      | as float fields on   |
|                      |                      | the Purchase         |
|                      |                      | settings page.       |
+----------------------+----------------------+----------------------+

Views
~~~~~

+----------------------------------+----------------------------------+
| File                             | Description                      |
+==================================+==================================+
| ``view                           | List, form, and action for       |
| s/po_approval_matrix_views.xml`` | ``xx.po.approval.matrix``.       |
|                                  | Accessible under Purchase →      |
|                                  | Configuration → Approval Matrix. |
+----------------------------------+----------------------------------+
| ``                               | Adds the *Approvers* tab         |
| views/purchase_order_views.xml`` | (dynamic approver lines) and the |
|                                  | *Department* field to the PO     |
|                                  | form view.                       |
+----------------------------------+----------------------------------+
| ``views/                         | Adds *Dynamic Approver*, *Board  |
| studio_approval_rule_views.xml`` | Approval*, and *Approval Group*  |
|                                  | columns/fields to the Studio     |
|                                  | approval rule list and form      |
|                                  | views.                           |
+----------------------------------+----------------------------------+
| ``views                          | Adds the *Board Approval         |
| /res_config_settings_views.xml`` | Signature* section to Purchase → |
|                                  | Configuration → Settings.        |
+----------------------------------+----------------------------------+
| ``views/seed_wizard_views.xml``  | Minimal form view and action for |
|                                  | the demo-data seed wizard.       |
+----------------------------------+----------------------------------+

Security
~~~~~~~~

+----------------------------------+----------------------------------+
| File                             | Description                      |
+==================================+==================================+
| ``security/ir.model.access.csv`` | ``xx.po.approval.matrix``: full  |
|                                  | CRUD for Purchase Manager,       |
|                                  | read-only for Purchase User.     |
|                                  | ``xx.po.approval.user``: full    |
|                                  | CRUD for Purchase User (required |
|                                  | so approvers can be assigned on  |
|                                  | the PO), read-only for all other |
|                                  | internal users.                  |
+----------------------------------+----------------------------------+

Tests
~~~~~

+----------------------------------+----------------------------------+
| File                             | Description                      |
+==================================+==================================+
| ``tests/te                       | Integration tests covering       |
| st_xx_approval_dynamic_user.py`` | matrix lookup, approval-line     |
|                                  | sync, sequential step            |
|                                  | enforcement, and board sign      |
|                                  | completion flow.                 |
+----------------------------------+----------------------------------+


Credits
=======

Maintainer
----------

.. image:: /xx_approval_dynamic_user/static/description/icon.png
  :alt: Dynapps
  :target: https://www.dynapps.eu
  :width: 88
  :height: 88

This module is maintained by Dynapps.