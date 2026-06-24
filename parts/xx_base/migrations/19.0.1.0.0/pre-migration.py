def migrate(cr, version):
    cr.execute(
        "DELETE FROM ir_embedded_actions"
        " WHERE parent_res_model='project.project'"
        " AND python_method='action_get_list_view'"
    )
