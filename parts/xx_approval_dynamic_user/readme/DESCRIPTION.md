Extends the Studio approval flow for Purchase Orders with dynamic, per-PO approver assignment and sequential step enforcement.

## Key features

- **Dynamic approver assignment** — each Studio approval rule marked as *Dynamic Approver* resolves its actual approver at PO level via the *Approvers* tab, rather than using a fixed group. Available approvers are looked up from a company/department/approval-group matrix.
- **Board member approval via Sign** — rules marked as *Board Approval* route the approval through the Sign module instead of an internal Odoo user. The PO PDF is rendered automatically, a signature field is placed on the last page, and a sign request is sent to the assigned board member.
- **Sequential steps** — approval steps fire one at a time in *Notification Order* sequence. A step's activity or sign request is only created once all lower-order steps carry an approved entry, preventing parallel triggering.
- **Approval matrix** — configurable per company, department (analytic account), and approver group. Internal users and external board members can both appear in the matrix. When exactly one candidate exists for a step, the approver is pre-filled automatically.
- **Signature placement settings** — the position and size of the signature field on the PO PDF can be configured under Purchase → Configuration → Settings (Board Approval Signature section).
- **Admin sign link** — administrators see a direct signing URL on board approval rows in the Approvers tab, allowing local testing without email delivery.

## Files

### New models
| File | Model | Description |
|---|---|---|
| `models/xx_po_approval_matrix.py` | `xx.po.approval.matrix` | Approval matrix rows mapping company + department (analytic account) + approver group to an internal user or external board member partner. |
| `models/xx_po_approval_user.py` | `xx.po.approval.user` | Per-PO approver assignment lines (one row per dynamic approval step). Tracks the assigned user or board member partner and links to the sign request for board steps. |
| `wizard/xx_seed_wizard.py` | `xx.seed.wizard` | Transient wizard that seeds demo departments, users, groups, Studio approval rules and matrix rows for testing. |

### Inherited models
| File | Inherits | What is added / overridden |
|---|---|---|
| `models/purchase_order.py` | `purchase.order` | Adds `xx_approval_line_ids` (O2M to `xx.po.approval.user`) and `xx_department_id` (M2O to analytic account). Syncs approval lines on create/write/onchange. Validates completeness before save. |
| `models/studio_approval_rule.py` | `studio.approval.rule` | Adds `is_dynamic_approver` and `is_board_approval` flags. Overrides `_compute_can_validate`, `check_approval`, `_create_request`, and `_set_approval` to enforce per-PO assignment and sequential step gating. Routes board steps to Sign. |
| `models/sign_request.py` | `sign.request` | Overrides `write` to detect when a sign request reaches `signed` state and auto-completes the linked board approval step on the PO. |
| `models/res_config_settings.py` | `res.config.settings` | Exposes four `ir.config_parameter` values (`board_sign_pos_x/y`, `board_sign_width/height`) as float fields on the Purchase settings page. |

### Views
| File | Description |
|---|---|
| `views/po_approval_matrix_views.xml` | List, form, and action for `xx.po.approval.matrix`. Accessible under Purchase → Configuration → Approval Matrix. |
| `views/purchase_order_views.xml` | Adds the *Approvers* tab (dynamic approver lines) and the *Department* field to the PO form view. |
| `views/studio_approval_rule_views.xml` | Adds *Dynamic Approver*, *Board Approval*, and *Approval Group* columns/fields to the Studio approval rule list and form views. |
| `views/res_config_settings_views.xml` | Adds the *Board Approval Signature* section to Purchase → Configuration → Settings. |
| `views/seed_wizard_views.xml` | Minimal form view and action for the demo-data seed wizard. |

### Security
| File | Description |
|---|---|
| `security/ir.model.access.csv` | `xx.po.approval.matrix`: full CRUD for Purchase Manager, read-only for Purchase User. `xx.po.approval.user`: full CRUD for Purchase User (required so approvers can be assigned on the PO), read-only for all other internal users. |

### Tests
| File | Description |
|---|---|
| `tests/test_xx_approval_dynamic_user.py` | Integration tests covering matrix lookup, approval-line sync, sequential step enforcement, and board sign completion flow. |
