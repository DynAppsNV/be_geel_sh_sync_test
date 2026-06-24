import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";
import { localization } from "@web/core/l10n/localization";
const { DateTime } = luxon;

registry.category("web_tour.tours").add("test_appointment_kanban_view_date_filter", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            {
                trigger: ".pos-leftheader button:contains('Booking')",
                run: "click",
            },
            {
                content: "Check that the date filter is applied by default",
                trigger: `.pos .date-filter:contains('${DateTime.now().toFormat(
                    "ccc " + localization.dateFormat
                )}')`,
            },
            {
                content: "Remove the date filter",
                trigger: ".pos .date-filter i.fa-close",
                run: "click",
            },
            {
                content: "Check that the date filter is not applied anymore",
                trigger: ".pos .date-filter:contains(Select Date)",
            },
        ].flat(),
});
