import { registry } from '@web/core/registry';

registry.category("web_tour.tours").add("hr_contract_salary_hidden_simulation_offer_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "Open Payroll App",
            trigger: ".o_app:contains('Payroll')",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Open Employees Menu",
            trigger: ".o_menu_sections button.dropdown-toggle:contains('Employees')", 
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Click Salary Calculator",
            trigger: ".dropdown-item:contains('Salary Calculator')",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Select employee",
            trigger: "div[name='simulation_employee_id'] input",
            run: "edit Simulation Test Employee",
            tooltipPosition: "bottom",
        },
        {
            content: "Select employee from autocomplete",
            trigger: ".o-autocomplete--dropdown-item span:contains('Simulation Test Employee')",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Enter salary amount",
            trigger: "div[name='final_yearly_costs'] input",
            run: "edit 120000",
            tooltipPosition: "bottom",
        },
        {
            content: "Wait for the backend computation to finish",
            trigger: "[name='yearly_employer_cost']:contains('120')",
            run: () => {},
        },
        {
            content: "Click Close Button",
            trigger: ".o_technical_modal footer button:contains('Close')",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Go back to Home",
            trigger: ".o_menu_toggle, .o_menu_brand",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Open Recruitment App",
            trigger: ".o_app:contains('Recruitment')",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Open Applications Menu",
            trigger: ".o_menu_sections button.dropdown-toggle:contains('Applications')",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Open Offers",
            trigger: ".dropdown-item:contains('Offers')",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Open custom filter menu",
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Add a custom filter",
            trigger: ".o_add_custom_filter",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Open field selector",
            trigger: ".o_model_field_selector_value",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Search simulation employee field",
            trigger: ".o_model_field_selector_popover_search > .o_input",
            run: "edit Simulation Employee",
            tooltipPosition: "bottom",
        },
        {
            content: "Select simulation employee field",
            trigger: ".o_model_field_selector_popover button:contains('Simulation Employee')",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Enter employee name in filter value",
            trigger: ".o-autocomplete--input",
            run: "edit Simulation Test Employee",
            tooltipPosition: "bottom",
        },
        {
            content: "Select employee from autocomplete",
            trigger: ".o-autocomplete--dropdown-item span:contains('Simulation Test Employee')",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Apply custom filter",
            trigger: ".o_technical_modal footer button:contains('Search')",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Ensure simulation offer is hidden",
            trigger: ".o_nocontent_help",
            run: () => {},
        },
    ]
});
