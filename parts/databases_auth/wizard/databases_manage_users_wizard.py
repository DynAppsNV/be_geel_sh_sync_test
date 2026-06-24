import logging
from odoo import models

from odoo.addons.databases.api import ApiError
# import from databases_auth.api to ensure the monkey patch is applied
from odoo.addons.databases_auth.api import OdooDatabaseApi


_logger = logging.getLogger(__name__)


class DatabasesInviteUsersWizard(models.TransientModel):
    _inherit = 'databases.manage_users.wizard'

    def _set_oauth_to_remote_dbs(self):
        db_users = self.database_ids.database_user_ids & self.user_ids.database_user_ids
        for db, db_users in db_users.grouped('project_id').items():
            args = [db.database_url, db.database_name, db.database_api_login, db.sudo().database_api_key_to_use]
            if not all(args):
                # stay smooth as this flow is ran when the user click on 'connect' button
                continue
            db_api = OdooDatabaseApi(*args)
            self._set_remote_oauth_id(db, db_api, db_users)

    def _set_remote_oauth_id(self, db, db_api, db_users):
        db.ensure_one()
        if db.database_hosting != 'saas':  # only make sense for saas which is guaranteed to have the field `oauth_uid`
            return

        for db_user in db_users:
            if not db_user.local_user_id.databases_sso_uid:
                continue
            try:
                db_api.set_user_oauth(db_user)
            except ApiError as e:
                _logger.warning('ApiError: Error while setting oauth_uid on user %s on %s: %s', db_user, db_api.database, e.args[0])
