from . import models


def post_init_hook(env):
    env["ir.module.module"].update_list()
