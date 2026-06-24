import { BankRecButtonList } from "../button_list/button_list";
import { BankRecLineToReconcile } from "../line_to_reconcile/line_to_reconcile";
import { BankRecReconciledLineName } from "../reconciled_line_name/reconciled_line_name";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { formatMonetary } from "@web/views/fields/formatters";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useEffect, useState, useRef } from "@odoo/owl";
import { useBankReconciliation } from "../bank_reconciliation_service";

export class BankRecStatementLine extends KanbanRecord {
    static template = "account_accountant.BankRecStatementLine";
    static components = {
        BankRecLineToReconcile,
        BankRecButtonList,
        DropdownItem,
        BankRecReconciledLineName,
    };
    static props = [...KanbanRecord.props];

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.ui = useService("ui");
        this.bankReconciliation = useBankReconciliation();
        this.state = useState({
            isUnfolded: false,
            accountMoveLines: [],
            linesToReconcile: [],
            suspenseAccountLine: undefined,
            reconciledLineName: {},
        });
        this.statementLineRootRef = useRef("root");
        if (this.env.model.config.context?.default_st_line_id === this.props.record.resId) {
            this.state.isUnfolded = true;
            this.bankReconciliation.selectStatementLine(this.props.record);
        }
        this._updateLinesState();
        onWillStart(async () => {
            this.userCanReview = await user.hasGroup("account.group_account_user");
        });
        useEffect(
            () => {
                this._updateLinesState();
            },
            () => [this.recordData.line_ids.records]
        );
    }

    getRecordClasses() {
        let classes = super.getRecordClasses();
        if (this.hasStatementLine === 1) {
            classes += " mt-3";
        }
        return classes;
    }

    // -----------------------------------------------------------------------------
    // ACTION
    // -----------------------------------------------------------------------------

    openStatementCreate() {
        this.action.doAction("account_accountant.action_bank_statement_form_bank_rec_widget", {
            additionalContext: {
                split_line_id: this.recordData.id,
                default_journal_id: this.recordData.journal_id.id,
            },
            onClose: async () => {
                this.env.model.load();
            },
        });
    }

    openPartner() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: this.partner.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async removePartner() {
        await this.orm.write("account.bank.statement.line", [this.recordData.id], {
            partner_id: false,
        });
        this.record.load();
    }

    async undoReconciliation() {
        await this.orm.call("account.bank.statement.line", "action_undo_reconciliation", [this.recordData.id]);
        this.record.load();
    }

    // -----------------------------------------------------------------------------
    // HELPER
    // -----------------------------------------------------------------------------
    _updateLinesState() {
        const suspenseId = this.recordData.journal_id?.suspense_account_id.id;
        const defaultId = this.recordData.journal_id?.default_account_id.id;
        const allLines = this.recordData.line_ids.records.map((line) => line.data);

        this.state.accountMoveLines = allLines;
        this.state.linesToReconcile = allLines.filter(
            (line) => line.account_id.id !== suspenseId && line.account_id.id !== defaultId
        );
        this.state.suspenseAccountLine = allLines.find((line) => line.account_id.id === suspenseId);

        this._computeReconciledLineName(this.state.linesToReconcile);
    }

    _computeReconciledLineName(linesToReconcile) {
        const reconciledLine = {};
        for (const line of linesToReconcile) {
            if (
                line.reconciled_lines_excluding_exchange_diff_ids.records.length === 1 &&
                line.reconciled_lines_excluding_exchange_diff_ids.records[0].data.move_name
            ) {
                reconciledLine[line.id] = {
                    move: line.reconciled_lines_excluding_exchange_diff_ids.records[0].data
                        .move_name,
                };
            } else if (line.tax_ids.count) {
                reconciledLine[line.id] = { tax: line.tax_ids.records };
            } else {
                reconciledLine[line.id] = { account: line.account_id.display_name };
            }
        }
        this.state.reconciledLineName = reconciledLine;
    }

    get record() {
        return this.props.record;
    }

    get recordData() {
        return this.props.record.data;
    }

    get accountMoveLines() {
        return this.state.accountMoveLines;
    }

    get linesToReconcile() {
        return this.state.linesToReconcile;
    }

    get suspenseAccountLine() {
        return this.state.suspenseAccountLine || undefined;
    }

    get reconciledLineName() {
        return this.state.reconciledLineName;
    }

    fold() {
        if (this.state.isUnfolded) {
            this.toggleUnfold();
        }
        this.selectStatementLine();
    }

    unfold() {
        if (!this.state.isUnfolded) {
            this.toggleUnfold();
        }
        this.selectStatementLine();
    }

    toggleUnfold(event) {
        if (event?.pointerType === 'mouse') {
            this.state.isUnfolded = !this.isUnfolded;
        }
        this.selectStatementLine(event);
    }

    selectStatementLine(event) {
        // In case we are on a mobile device, we want to keep the old onClick behaviour
        if (this.recordData.is_reconciled && event?.pointerType !== 'mouse') {
            this.state.isUnfolded = !this.isUnfolded;
        }
        // Update the chatter with the last selected element
        this.bankReconciliation.selectStatementLine(this.record);
    }

    openChatter() {
        this.bankReconciliation.selectStatementLine(this.record);
        this.bankReconciliation.openChatter();
    }

    get hasInvalidAnalytics() {
        return this.linesToReconcile.some((line) => line.has_invalid_analytics);
    }

    get isUnfolded() {
        return this.state.isUnfolded;
    }

    get hasStatementLine() {
        return this.env.model.root.count;
    }

    get formattedAmount() {
        return formatMonetary(this.recordData.amount, {
            currencyId: this.recordData.currency_id.id,
        });
    }

    get formattedDate() {
        return this.recordData.date.toLocaleString({
            month: "short",
            day: "2-digit",
        });
    }

    get formattedFullDate() {
        return this.recordData.date.toLocaleString({
            month: "long",
            day: "numeric",
            year: "numeric",
        });
    }

    get partner() {
        return this.recordData.partner_id;
    }

    get hasForeignCurrencyAndSameCurrencyForAllLines() {
        return (
            this.recordData.foreign_currency_id &&
            this.linesToReconcile.length > 0 &&
            this.linesToReconcile.every(
                (line) => line.currency_id.id === this.recordData.foreign_currency_id.id
            )
        );
    }

    get suspenseAccountLineFormattedAmount() {
        return formatMonetary(this.suspenseAccountLine.amount_currency, {
            currencyId: this.suspenseAccountLine?.currency_id.id,
        });
    }

    get activityNumber() {
        return this.recordData.activity_ids.count;
    }

    /**
     * Checks if there is at least one attachment associated with the bank statement line or its related records.
     *
     * This getter aggregates attachment counts from:
     * - The bank statement line record itself or the related move since attachment_ids is a related to move_id.attachment_ids.
     * - The related move lines themselves, if they have attachments directly associated (`line.move_attachment_ids`)
     *   except the attachments link to the statement.
     * - The lines reconciled with the related move lines, specifically checking for attachments on the
     *   move associated with those reconciled lines.
     *
     * This check ensures that all attachments from associated invoices, bills, and other related documents are considered.
     *
     * @returns {number} The total number of attachments found. A return value greater than 0 indicates the presence of attachments.
     */
    get hasAttachment() {
        const statementAttachment = this.recordData.bank_statement_attachment_ids.records.map(
            (attachment) => attachment.data.id
        );
        const lines = this.linesToReconcile;

        return (
            this.recordData.attachment_ids.records.length +
            lines
                .flatMap((line) => line.reconciled_lines_ids.records)
                .filter((line) => line.data.move_attachment_ids?.count)
                .reduce(
                    (accumulator, line) =>
                        parseInt(accumulator) + parseInt(line.data.move_attachment_ids.count),
                    0
                ) +
            lines
                .filter(
                    (line) =>
                        line.move_attachment_ids?.count &&
                        !line.move_attachment_ids.records
                            .map((attachment) => attachment.data.id)
                            .every((id) => statementAttachment.includes(id))
                )
                .reduce(
                    (accumulator, line) =>
                        parseInt(accumulator) + parseInt(line.move_attachment_ids.count),
                    0
                )
        );
    }

    get amountClasses() {
        const classes = this.recordData.foreign_currency_id ? "w-50" : "w-100";
        if (this.recordData.amount > 0) {
            return `${classes} fw-bold`;
        }
        if (this.recordData.amount < 0) {
            return `${classes} text-danger fw-bold`;
        }
        return `${classes} text-secondary`;
    }

    get buttonListProps() {
        return {
            statementLineRootRef: this.statementLineRootRef,
            statementLine: this.record,
            reconcileLineCount:
                this.bankReconciliation.reconcileCountPerPartnerId[this.recordData.partner_id.id] ??
                null,
            reconcileModels:
                this.bankReconciliation.reconcileModelPerStatementLineId[this.recordData.id] ?? [],
            preSelectedReconciliationModel: this.accountMoveLines
                .filter((line) => line.reconcile_model_id.id)
                .map((line) => line.reconcile_model_id)?.[0],
        };
    }

    get formattedAmountCurrencyInForeign() {
        return formatMonetary(this.recordData.amount_currency, {
            currencyId: this.recordData.foreign_currency_id.id,
        });
    }

    get isSelected() {
        return this.recordData.move_id.id === this.bankReconciliation.statementLineMoveId;
    }

    get isChatterOpen() {
        return this.bankReconciliation.chatterState.visible;
    }
}
