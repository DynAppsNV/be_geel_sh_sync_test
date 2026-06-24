import { patch } from "@web/core/utils/patch";
import { Dropdown } from "@web/core/dropdown/dropdown";

patch(Dropdown.prototype, {
    /**
     * Embedded views in knowledge can become the active element, but dropdowns
     * should be able to be closed by clicking outside the embedded view.
     *
     * @override
     */
    popoverCloseOnClickAway(target, dropdownActiveEl) {
        if (dropdownActiveEl === undefined) {
            // Done as a fix. https://github.com/odoo/odoo/commit/1fb00045c6826e
            // removed the activeEl parameter, and inverted the need for this
            // patch (before, it was needed to be able to close dropdowns by
            // clicking inside the embed, it is now needed to be able to close
            // them by clicking outside the embed). In 19.2, this patch could be
            // removed entirely as https://github.com/odoo/odoo/commit/48be3442b
            // made a generic solution for this to work (it will probably be
            // done once this reaches master though).
            dropdownActiveEl = this.activeEl;
        }
        const currentActiveEl = this.uiService.getActiveElementOf(target);
        return (
            super.popoverCloseOnClickAway(target, dropdownActiveEl) ||
            (dropdownActiveEl.dataset?.embedded &&
                currentActiveEl !== dropdownActiveEl &&
                currentActiveEl.contains(dropdownActiveEl))
        );
    },
});
