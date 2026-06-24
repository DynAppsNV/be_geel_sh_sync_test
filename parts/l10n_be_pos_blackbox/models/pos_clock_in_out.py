from odoo import models, fields


class PosClockInOut(models.Model):
    # This model stores clock in and clock out events for users/employees in POS sessions. It's used in the user report at the end of a session.
    _name = 'pos.clock.in.out'
    _description = 'POS Clock In/Out Event of user/employee'

    type = fields.Selection([('in', 'Clock In'), ('out', 'Clock Out')], required=True, string='Type')
    session_id = fields.Many2one('pos.session', required=True, string='POS Session')
    user_id = fields.Many2one('res.users', string='User')
    event_date_time = fields.Datetime(required=True, string='Event DateTime', default=fields.Datetime.now)
