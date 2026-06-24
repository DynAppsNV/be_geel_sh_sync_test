import { useEffect } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { SearchBar } from "@point_of_sale/app/screens/ticket_screen/search_bar/search_bar";

patch(SearchBar.prototype, {
    setup() {
        super.setup();
        useEffect(
            () => {
                this.state.searchInput =
                    this.props.config.defaultSearchDetails.searchTerm ||
                    this.state.searchInput ||
                    "";
            },
            () => [this.props.config.defaultSearchDetails]
        );
    },
});
