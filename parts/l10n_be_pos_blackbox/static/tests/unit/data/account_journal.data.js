import { AccountJournal } from "@point_of_sale/../tests/unit/data/account_journal.data";

AccountJournal._records = AccountJournal._records.map((record) => ({
    ...record,
    company_id: 2,
}));
