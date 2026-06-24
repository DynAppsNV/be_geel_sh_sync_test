from odoo import fields, models

PARAM = "xx_approval_dynamic_user.board_sign_{}"
DEFAULTS = {"pos_x": 0.70, "pos_y": 0.90, "width": 0.20, "height": 0.05}


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    xx_board_sign_pos_x = fields.Float(
        string="Signature X position",
        config_parameter=PARAM.format("pos_x"),
        default=DEFAULTS["pos_x"],
        help="Horizontal position of the signature field (0 = left, 1 = right).",
    )
    xx_board_sign_pos_y = fields.Float(
        string="Signature Y position",
        config_parameter=PARAM.format("pos_y"),
        default=DEFAULTS["pos_y"],
        help="Vertical position of the signature field (0 = top, 1 = bottom).",
    )
    xx_board_sign_width = fields.Float(
        string="Signature width",
        config_parameter=PARAM.format("width"),
        default=DEFAULTS["width"],
    )
    xx_board_sign_height = fields.Float(
        string="Signature height",
        config_parameter=PARAM.format("height"),
        default=DEFAULTS["height"],
    )
