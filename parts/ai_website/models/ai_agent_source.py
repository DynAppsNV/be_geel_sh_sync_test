# Part of Odoo. See LICENSE file for full copyright and licensing details.
from urllib.parse import urlparse

from odoo import models


class AIAgentSource(models.Model):
    _inherit = 'ai.agent.source'

    def _get_internal_domains(self):
        """
        OVERRIDE
        Get a clean list of unique internal domains.
        Handles protocols, paths, and punycode fallback.
        :return: list of internal domains
        :rtype: list of str
        """
        websites = self.env['website'].search([])
        raw_values = [site.domain_punycode or site.domain for site in websites]
        base_url = self.get_base_url()
        raw_values.append(base_url)
        internal_domains = set()
        for raw_value in raw_values:
            if not raw_value:
                continue
            parsed = urlparse(raw_value)
            domain = parsed.netloc or parsed.path.split('/')[0]
            domain = domain.split(':')[0]
            if domain:
                internal_domains.add(domain.lower().strip())
        return list(internal_domains)
