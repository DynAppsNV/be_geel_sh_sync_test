from odoo import models


class ProjectTemplateCreateWizard(models.TransientModel):
    _inherit = 'project.template.create.wizard'

    def _create_project_from_template(self):
        context = dict(self.env.context)
        if self.template_id.is_fsm:
            context.pop('default_sale_line_id', None)
            context.pop('default_sale_order', None)
            context.pop('default_reinvoiced_sale_order_id', None)
        return super(ProjectTemplateCreateWizard, self.with_context(context))._create_project_from_template()
