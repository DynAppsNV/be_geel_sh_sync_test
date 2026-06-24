import hashlib
import pathlib

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request
from odoo.modules import get_module_path

BLACKBOX_MODULES = ['l10n_be_pos_blackbox', 'l10n_be_pos_blackbox_self_order', 'l10n_be_pos_blackbox_loyalty', 'l10n_be_pos_blackbox_settle_due']


class GovCertificationController(http.Controller):

    @http.route('/l10n_be_pos_blackbox_source', auth='user')
    def handler(self):
        if not request.env.user.has_group('base.group_user'):
            raise Forbidden()

        root = pathlib.Path(__file__).parent.parent.parent

        modfiles = [
            p
            for modpath in map(pathlib.Path, map(get_module_path, BLACKBOX_MODULES))
            for p in modpath.glob('**/*')
            if p.is_file()
            if p.suffix in ('.py', '.xml', '.js', '.csv')
            if '/tests/' not in str(p)
        ]
        modfiles.sort()

        files_data = []
        main_hash = hashlib.sha1()
        for p in modfiles:
            content = p.read_bytes()
            content_hash = hashlib.sha1(content).hexdigest()
            files_data.append({
                'name': str(p.relative_to(root)),
                'size_in_bytes': p.stat().st_size,
                'hash': content_hash
            })
            main_hash.update(content_hash.encode())

        data = {
            'files': files_data,
            'main_hash': main_hash.hexdigest(),
        }

        return request.render('l10n_be_pos_blackbox.fdm_source', data, mimetype='text/plain')
