from lxml import etree

from odoo import api, models


class DashboardSmartButton(models.AbstractModel):
    _name = "dashboard.smart.button.mixin"
    _description = "Dashboard Smart button mixin"

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == "form":
            smart_buttons = self._get_dashboard_smart_button()
            parent_node = arch.find("sheet")
            if parent_node is not None:
                buttonbox_node = parent_node.xpath("//div[@name='button_box']")
                if buttonbox_node:
                    for button in smart_buttons:
                        buttonbox_node[0].append(button)
                else:
                    # create the button box ourselves
                    buttonbox_node = etree.fromstring(
                        '<div class="oe_button_box" name="button_box"/>'
                    )
                    # get the first element so we can prepend
                    first_elements = arch.xpath("//sheet/*[1]")
                    if first_elements is not None:
                        first_elements = first_elements[0]
                        for button in smart_buttons:
                            buttonbox_node.append(button)
                        first_elements.addprevious(buttonbox_node)
        return arch, view

    def button_open_dashboard(self):
        action = self.env["ir.actions.actions"]._for_xml_id("dyn_dashboard.dyn_my_dashboard_action")
        action["context"] = self.with_context(odoo_record_id=self.id).env.context
        action["domain"] = [("odoo_record_id", "=", self.id)]
        return action

    def _get_dashboard_smart_button(self):
        model_id = self.env["ir.model"].search([("model", "=", self._name)]).id
        dashboards = self.env["xx.dashboard"].search([("model_ids", "in", model_id)])
        buttons = []
        for dashboard in dashboards:
            if dashboard.icon:
                dashboard_icon_html = dashboard.icon
            else:
                dashboard_icon_html = "fa-line-chart"
            context = f"{{'dashboard_id': {dashboard.id}}}"
            buttonstring = f"""
                <button type="object"
                    name="button_open_dashboard"
                    class="oe_stat_button"
                    icon="{dashboard_icon_html}"
                    context="{context}">
                    <div class="o_stat_info">
                        <span class="o_stat_text">{dashboard.name}</span>
                    </div>
                </button>"""
            button = etree.fromstring(buttonstring)
            buttons.append(button)
        return buttons
