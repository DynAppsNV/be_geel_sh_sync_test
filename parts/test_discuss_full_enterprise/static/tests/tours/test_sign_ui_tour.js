import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

/**
 * This tour ensures the sign request option is present in the cog menu
 * of the Project form view when accessing it from a specific path.
 *
 * This test targets an issue in which the presence of the chatter,
 * which the option depends on, was not recognized when accessing views
 * from certain actions and contexts.
 *
 * This tour was added in this module because it ensures both the Project
 * and Sign modules are installed.
 */
registry.category("web_tour.tours").add("test_sign_ui_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Project APP",
            trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
            run: "click",
        },
        {
            content: "Click on any Project",
            trigger: 'span:contains("Test Sign Project")',
            run: "click",
        },
        {
            content: "Ensure we are in Task view",
            trigger: 'a.fw-bold.text-truncate:contains("Projects")',
        },
        {
            content: "Click on any Task",
            trigger: "article",
            run: "click",
        },
        {
            content: "Click the internal link to the project",
            trigger:
                'div[name="project_id"]>div.d-flex>div.o_many2one>div.o_field_many2one_selection>button:not(:visible)',
            run: "click",
        },
        {
            content: "Wait for next view to load",
            trigger: 'button[name="action_view_tasks"]',
        },
        {
            content: "Select the dropdown cog menu",
            trigger: "button:has(i.fa-cog)",
            run: "click",
        },
        {
            content: "Ensure the 'Request signature' option is present",
            trigger: ".o_sign_request",
            run: "click",
        },
        {
            content: "Confirm the signature request modal is opened",
            trigger: 'div.modal-content > header > h4.modal-title:contains("Signature Request")',
        },
    ],
});
