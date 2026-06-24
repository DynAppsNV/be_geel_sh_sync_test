from odoo import fields, models, api, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools.misc import format_date

import base64
import json
import os
import re
import requests
import uuid
import xmlsec
from cryptography import x509
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.serialization import Encoding
from tempfile import NamedTemporaryFile
from odoo.tools import zeep
from odoo.tools.zeep import Client, wsse, wsa
from odoo.tools.zeep.exceptions import Fault
from lxml import etree
from lxml.etree import Element
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from OpenSSL import crypto
from contextlib import suppress
from urllib3.util.ssl_ import create_urllib3_context
from urllib3.contrib.pyopenssl import inject_into_urllib3
from urllib3.connectionpool import HTTPSConnectionPool
from requests.exceptions import SSLError
from stdnum.nl.btw import compact


class SoapClientWrapper:
    def create_soap_client(self, wsdl_address, root_cert_file, client_cert, client_pkey):
        # The Zeep module uses a Client which will handle the creation and signature of the SOAP message sent to the government system.
        try:
            session = requests.Session()
            adapter = MemoryCertificateAndKeyHTTPAdapter()
            session.mount('https://', adapter)
            session.cert = (client_cert, client_pkey)
            session.verify = root_cert_file.name
            signature = BinarySignatureTimestamp(client_pkey, client_cert, adapter=adapter)
            plugins = [WsaSBR()]
            return Client(wsdl_address, wsse=signature, session=session, plugins=plugins)
        except SSLError as e:
            # The certificate was not accepted by the government server
            raise UserError(_("An error occurred while using your certificate. Please verify the certificate you uploaded and try again.")) from e

    def create_soap_client_logius(self, wsdl_address, root_cert_file, client_cert, client_pkey, trusted_roots_pem, service_address):
        # The Zeep module uses a Client which will handle the creation and signature of the SOAP message sent to the government system.
        try:
            session = requests.Session()
            adapter = MemoryCertificateAndKeyHTTPAdapter()
            session.mount('https://', adapter)
            session.cert = (client_cert, client_pkey)
            session.verify = root_cert_file.name
            signature = BinarySignatureTimestamp(client_pkey, client_cert, trusted_roots=trusted_roots_pem, adapter=adapter)
            plugins = [WsaSBR()]
            client = Client(wsdl_address, wsse=signature, session=session, plugins=plugins)
            service = next(iter(client._Client__obj.wsdl.services.values()))
            port = next(iter(service.ports.values()))
            service_proxy = client.create_service(port.binding.name, service_address)
        except SSLError as e:
            # The certificate was not accepted by the government server
            raise UserError(_("An error occured while using your certificate. Please verify the certificate you uploaded and try again.")) from e
        return client, service_proxy


def _sign_envelope_with_key_binary(envelope, key):
    """ Modifies the signature of the envelope to match the Dutch government system specification.
        Basically a copy of the original code from the zeep library with some adjustments.
    """
    cert_data = envelope.attrib.pop('data-l10n-nl-signing-cert').encode()
    security, sec_token_ref, x509_data = _signature_prepare(envelope, key)
    ref = etree.SubElement(sec_token_ref, etree.QName(zeep.ns.WSSE, 'Reference'),
                           {'ValueType': 'http://docs.oasis-open.org/wss/2004/01/'
                                         'oasis-200401-wss-x509-token-profile-1.0#X509v3'})
    ref_id = wsse.utils.get_unique_id()
    ref.set('URI', '#' + ref_id)
    bintok = etree.Element(etree.QName(zeep.ns.WSSE, 'BinarySecurityToken'), {
        etree.QName(zeep.ns.WSU, 'Id'): ref_id,
        'ValueType': 'http://docs.oasis-open.org/wss/2004/01/'
                     'oasis-200401-wss-x509-token-profile-1.0#X509v3',
        'EncodingType': 'http://docs.oasis-open.org/wss/2004/01/'
                        'oasis-200401-wss-soap-message-security-1.0#Base64Binary'})
    certificate_der = x509.load_pem_x509_certificate(cert_data).public_bytes(Encoding.DER)
    bintok.text = base64.b64encode(certificate_der).decode()
    security.insert(0, bintok)
    x509_data.getparent().remove(x509_data)


def _signature_prepare(envelope, key):
    """ Prepare the envelope and sign.
        Basically a copy of the original code from the zeep library with some adjustments.
    """
    soap_env = wsse.signature.detect_soap_env(envelope)

    # Create the Signature node.
    signature = xmlsec.template.create(
        envelope,
        xmlsec.Transform.EXCL_C14N,
        xmlsec.Transform.RSA_SHA1,
    )

    key_info = xmlsec.template.ensure_key_info(signature)
    x509_data = xmlsec.template.add_x509_data(key_info)
    xmlsec.template.x509_data_add_issuer_serial(x509_data)
    xmlsec.template.x509_data_add_certificate(x509_data)

    security = wsse.utils.get_security_header(envelope)
    security.insert(0, signature)

    ctx = xmlsec.SignatureContext()
    ctx.key = key
    header = envelope.find(etree.QName(soap_env, 'Header'))
    wsse.signature._sign_node(ctx, signature, envelope.find(etree.QName(soap_env, 'Body')))
    wsse.signature._sign_node(ctx, signature, security.find(etree.QName(zeep.ns.WSU, 'Timestamp')))
    wsse.signature._sign_node(ctx, signature, header.find(etree.QName(zeep.ns.WSA, 'Action')))
    wsse.signature._sign_node(ctx, signature, header.find(etree.QName(zeep.ns.WSA, 'MessageID')))
    wsse.signature._sign_node(ctx, signature, header.find(etree.QName(zeep.ns.WSA, 'To')))
    wsse.signature._sign_node(ctx, signature, header.find(etree.QName(zeep.ns.WSA, 'ReplyTo')))
    ctx.sign(signature)

    sec_token_ref = etree.SubElement(
        key_info, etree.QName(zeep.ns.WSSE, 'SecurityTokenReference'))
    return security, sec_token_ref, x509_data


class PatchedHTTPSConnectionPool(HTTPSConnectionPool):

    def _make_request(
        self, conn, method, url, timeout=object(), chunked=False, **httplib_request_kw
    ):
        # OVERRIDE
        # We want to store the certificate we get from the server at the moment of the handshake (and after verificiation)
        # as we want to use it further in the process (for signature verification).
        httplib_response = super()._make_request(
            conn=conn,
            method=method,
            url=url,
            timeout=timeout,
            chunked=chunked,
            **httplib_request_kw
        )

        self._adapter.server_leaf_cert = conn.sock.connection.get_peer_certificate().to_cryptography().public_bytes(Encoding.PEM)
        peer_chain = conn.sock.connection.get_peer_cert_chain() or []
        self._adapter.server_intermediate_certs = [
            c.to_cryptography().public_bytes(Encoding.PEM)
            for c in peer_chain[1:]
        ]
        return httplib_response


class MemoryCertificateAndKeyHTTPAdapter(requests.adapters.HTTPAdapter):
    """ This adapter allows the use of in-memory cert and key, as we want to load them not as files, but from database. """

    def __init__(self):
        super().__init__()
        self.server_leaf_cert = None
        self.server_intermediate_certs = []

    def init_poolmanager(self, *args, **kwargs):
        # We need inject_into_urllib3 as it forces the adapter to use PyOpenSSL.
        # With PyOpenSSL, we can further patch the code to make it do what we want (with the use of SSLContext).
        inject_into_urllib3()
        kwargs["ssl_context"] = create_urllib3_context()
        return super().init_poolmanager(*args, **kwargs)

    def cert_verify(self, conn, url, verify, cert):
        # OVERRIDE
        # The original method wants to check for an existing file
        # at the cert location. As we use in-memory objects,
        # we skip the check and assign it manually.
        super().cert_verify(conn, url, verify, None)
        conn.cert_file = cert
        conn.key_file = None

    def get_connection(self, url, proxies=None):
        # OVERRIDE
        # Patch the OpenSSLContext to decode the certificate in-memory.
        # Bind this adapter instance into a subclass so PatchedHTTPSConnectionPool can write
        # TLS cert data back to the adapter without relying on module-level globals.
        adapter = self

        class _BoundHTTPSPool(PatchedHTTPSConnectionPool):
            _adapter = adapter

        self.poolmanager.pool_classes_by_scheme['https'] = _BoundHTTPSPool
        connection = super().get_connection(url, proxies=proxies)
        context = connection.conn_kw['ssl_context']

        def patched_load_cert_chain(certfile, keyfile=None, password=None):
            context._ctx.use_certificate(crypto.load_certificate(crypto.FILETYPE_PEM, certfile[0]))
            context._ctx.use_privatekey(crypto.load_privatekey(crypto.FILETYPE_PEM, certfile[1]))

        context.load_cert_chain = patched_load_cert_chain
        return connection


class BinarySignatureTimestamp(wsse.BinarySignature):
    """
        This signature use in-memory certificate and private key
        and applies a different timestamp and modified signature format.
    """
    def __init__(
        self,
        key_file,
        certfile,
        password=None,
        trusted_roots=None,
        adapter=None,
    ):
        # The init method from BinarySignature wants filepath, not stored-in-memory values.
        # The alternative to keep using in-memory certificate and key is with MemorySignature.
        # pylint: disable=super-init-not-called
        # pylint: disable=non-parent-init-called
        wsse.signature.MemorySignature.__init__(
            self,
            key_file,
            certfile,
            password,
        )
        # Parse the PEM bundle into trusted root anchors and untrusted intermediates.
        # Only self-signed certificates (subject == issuer) are genuine root CAs and should be
        # added to the X509Store as trust anchors. Non-self-signed certificates from the bundle
        # are intermediates: they help build the chain but must not be unconditionally trusted,
        # otherwise a compromised intermediate would bypass root CA validation.
        self._adapter = adapter
        self._trusted_roots = []         # self-signed root CAs → store.add_cert()
        self._bundle_intermediates = []  # non-self-signed CAs  → untrusted chain helpers
        if trusted_roots:
            pem_data = trusted_roots if isinstance(trusted_roots, bytes) else trusted_roots.encode()
            for match in re.finditer(rb'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', pem_data, re.DOTALL):
                with suppress(crypto.Error):
                    cert = crypto.load_certificate(crypto.FILETYPE_PEM, match.group(0))
                    if cert.get_subject().der() == cert.get_issuer().der():
                        self._trusted_roots.append(cert)
                    else:
                        self._bundle_intermediates.append(cert)

    def apply(self, envelope, headers):
        # OVERRIDE
        # Change the timestamp format and apply the new signature
        security = wsse.utils.get_security_header(envelope)

        created = datetime.utcnow()
        expired = created + timedelta(seconds=10 * 60)

        timestamp = wsse.utils.WSU('Timestamp')
        timestamp.append(wsse.utils.WSU('Created', created.isoformat() + 'Z'))
        timestamp.append(wsse.utils.WSU('Expires', expired.isoformat() + 'Z'))

        security.append(timestamp)

        key = wsse.signature._make_sign_key(self.key_data, self.cert_data, self.password)
        # Small trick to pass the certificate data to the signing method.
        # We need it to apply the signature in the way the Dutch government requires.
        envelope.attrib['data-l10n-nl-signing-cert'] = self.cert_data.decode()
        _sign_envelope_with_key_binary(envelope, key)

        return envelope, headers

    def verify(self, envelope):
        # Verify the server message signature with the server certificate that we grabbed during the first handshake.
        wsse.signature._make_verify_key(self._adapter.server_leaf_cert if self._adapter else None)
        soap_env = wsse.signature.detect_soap_env(envelope)

        header = envelope.find(etree.QName(soap_env, 'Header'))
        if header is None:
            raise wsse.signature.SignatureVerificationFailed()

        security = header.find(etree.QName(zeep.ns.WSSE, 'Security'))
        if security is None and envelope.find(etree.QName(soap_env, "Body")) and envelope.find(etree.QName(soap_env, "Body")).find(etree.QName(soap_env, "Fault")):
            # In case of a Fault response, the message is not signed. If the message contains the Fault tag, then the signature verification is skipped.
            return envelope
        signature = security.find(etree.QName(zeep.ns.DS, 'Signature'))

        ctx = xmlsec.SignatureContext()

        binary_token = security.find(etree.QName(zeep.ns.WSSE, 'BinarySecurityToken'))
        try:
            der_cert = base64.b64decode(binary_token.text)
            cert_pem = x509.load_der_x509_certificate(der_cert).public_bytes(Encoding.PEM)
        except (ValueError, TypeError):
            raise wsse.signature.SignatureVerificationFailed()

        # Verify that the signing cert (from the SOAP message) chains to our trusted root.
        if not self._is_trusted_signing_cert(cert_pem):
            raise wsse.signature.SignatureVerificationFailed(_("The signing certificate is not trusted."))

        # Find each signed element and register its ID with the signing context.
        refs = signature.iterfind('ds:SignedInfo/ds:Reference', namespaces={'ds': zeep.ns.DS})
        for ref in refs:
            # Get the reference URI and cut off the initial '#'
            referenced_id = ref.get('URI')[1:]
            referenced = envelope.find(".//*[@wsu:Id='%s']" % referenced_id, namespaces={'wsu': zeep.ns.WSU})
            ctx.register_id(referenced, 'Id', zeep.ns.WSU)

        ctx.key = wsse.signature._make_verify_key(cert_pem)

        try:
            ctx.verify(signature)
        except xmlsec.Error:
            raise wsse.signature.SignatureVerificationFailed()
        return envelope

    def _is_trusted_signing_cert(self, cert_pem):
        """Return True if cert_pem chains to a trusted Digipoort root and is valid for signing.

        Note: revocation checking (CRL/OCSP) is not performed. OpenSSL's X509StoreContext does not
        fetch CRL distribution points or query OCSP unless explicitly configured with CRL data.
        For high-assurance environments, supply a pre-fetched CRL to store.add_crl() and set
        X509StoreFlags.CRL_CHECK | CRL_CHECK_ALL, or accept this as a documented residual risk.
        """
        if not self._trusted_roots:
            return False
        try:
            store = crypto.X509Store()
            for root_cert in self._trusted_roots:
                store.add_cert(root_cert)
            candidate = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem)
            # Untrusted chain helpers: intermediates from the configured bundle + intermediates
            # captured from the TLS handshake. Neither set is trusted unconditionally; they are
            # only used to build the certificate path up to a trusted root anchor.
            intermediates = list(self._bundle_intermediates)
            for ic_pem in (self._adapter.server_intermediate_certs if self._adapter else []):
                with suppress(crypto.Error):
                    intermediates.append(crypto.load_certificate(crypto.FILETYPE_PEM, ic_pem))
            crypto.X509StoreContext(store, candidate, intermediates).verify_certificate()
        except (crypto.X509StoreContextError, crypto.Error):
            return False
        return self._cert_has_signing_purpose(cert_pem)

    def _cert_has_signing_purpose(self, cert_pem):
        """Return True if the cert does not explicitly forbid digital signatures.

        Some government signing certificates use EKU profiles that do not match generic
        server/client expectations. Enforce only the cryptographically relevant Key Usage
        constraint when it is present and treat EKU as informational.
        """
        try:
            cert = x509.load_pem_x509_certificate(cert_pem)
            try:
                ku = cert.extensions.get_extension_for_class(x509.KeyUsage).value
                # Accept digital_signature or content_commitment (non-repudiation) as signing-capable.
                signing_ku = ku.digital_signature or ku.content_commitment
                if not signing_ku:
                    return False
            except x509.ExtensionNotFound:
                pass  # No Key Usage extension; do not reject — some PKIoverheid certs omit it.
            return True
        except (ValueError, TypeError, UnsupportedAlgorithm):
            return False


class WsaSBR(wsa.WsAddressingPlugin):
    def egress(self, envelope, http_headers, operation, binding_options):
        # The Dutch government wants an additional address in the envelope header
        senvelope, shttp_headers = super().egress(envelope, http_headers, operation, binding_options)
        header = zeep.wsdl.utils.get_or_create_header(senvelope)
        header.extend([wsa.WSA.ReplyTo(wsa.WSA.Address('http://www.w3.org/2005/08/addressing/anonymous'))])
        return senvelope, shttp_headers


class L10n_Nl_ReportsSbrTaxReportWizard(models.TransientModel):
    _name = 'l10n_nl_reports.sbr.tax.report.wizard'
    _description = 'L10n NL Tax Report for SBR Wizard'

    def _get_default_initials(self):
        user_name = self.env.user.name
        return ''.join([name[0].upper() for name in re.split(r"[- ']", user_name)])

    def _get_default_infix(self):
        # The infix is the "little names" in-between the surname and last name (typically "van de")
        user_name = self.env.user.name
        user_names = user_name.split()
        return ' '.join(user_names[1:-1]) if len(user_names) > 2 else False

    date_from = fields.Date(string="Period Starting Date")
    date_to = fields.Date(string="Period Ending Date")
    can_report_be_sent = fields.Boolean(compute='_compute_sending_conditions')

    contact_initials = fields.Char(string="Contact Initials", default=_get_default_initials)
    contact_prefix = fields.Char(string="Contact Name Infix", default=_get_default_infix)
    contact_surname = fields.Char(string="Contact Last Name", default=lambda self: self.env.user.name.split()[-1])
    contact_phone = fields.Char(string="Contact Phone", default=lambda self: self.env.user.phone)
    contact_type = fields.Selection([('BPL', 'Taxpayer (BPL)'), ('INT', 'Intermediary (INT)')], string="Contact Type", default='BPL', required=True,
        help="BPL: if the taxpayer files a turnover tax return as an individual entrepreneur."
        "INT: if the turnover tax return is made by an intermediary.")
    tax_consultant_order = fields.Selection([
            ('NBA', 'NBA - Accountants'),
            ('RB', 'RB - Register of Tax Advisors'),
            ('NOB', 'NOB - Dutch Order of Tax Advisors'),
            ('NOAB', 'NOAB - Dutch Order of Administrative and Tax Experts'),
        ], default='NBA', required=True, string="Tax Consultant Order",
        compute="_compute_tax_consultant_order", readonly=False,
        help="The order of tax consultants the tax consultant belongs to."
    )
    tax_consultant_number = fields.Char(string="Tax Consultant Number", help="The tax consultant number of the office aware of the content of this report.")
    is_test = fields.Boolean(string="Is Test", help="Check this if you want the system to use the pre-production environment. A valid PKIoverheid certificate is required for both pre-production and production environments.")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('date_to', 'date_from', 'is_test')
    def _compute_sending_conditions(self):
        for wizard in self:
            wizard.can_report_be_sent = wizard.is_test or (
                wizard.env.company.tax_lock_date and wizard.env.company.tax_lock_date >= wizard.date_to
                and (
                    not wizard.env.company.l10n_nl_reports_sbr_last_sent_date_to
                    or wizard.date_from > wizard.env.company.l10n_nl_reports_sbr_last_sent_date_to
                    or wizard.date_to < wizard.env.company.l10n_nl_reports_sbr_last_sent_date_to + relativedelta(months=1)  # Users can send their report multiple times: the newest submission will replace the older ones.
                )
            )

    def _compute_tax_consultant_order(self):
        self.tax_consultant_order = self.tax_consultant_order or 'NBA'

    def _check_values(self):
        if self.env.company.account_representative_id:
            if not self.env.company.account_representative_id.vat:
                raise RedirectWarning(
                    _("Your accounting firm does not have a VAT number set. Please set it up before trying to send the report."),
                    self.env.ref('base.action_res_company_form').id,
                    _("Company Settings")
                )
        elif not self.env.company.vat:
            raise RedirectWarning(
                _("Your company does not have a VAT number set. Please set it up before trying to send the report."),
                self.env.ref('base.action_res_company_form').id,
                _("Company Settings")
            )

    def _get_sbr_identifier(self, options=None):
        if self.env.company.l10n_nl_reports_sbr_ob_nummer:
            return self.env.company.l10n_nl_reports_sbr_ob_nummer

        vat = self.env.company.vat
        if options and options.get('report_id'):
            report = self.env['account.report'].browse(options['report_id'])
            vat = report.get_vat_for_export(options, raise_warning=False)
        return compact(vat) if vat else ''

    def _additional_processing(self, options, kenmerk, closing_move):
        self.env['l10n_nl_reports.sbr.status.service'].create({
            'kenmerk': kenmerk,
            'company_id': self.env.company.id,
            'report_name': self.env['account.report'].browse(options['report_id']).name,
            'closing_entry_id': closing_move and closing_move.id,
            'is_test': self.is_test,
        })
        status_service_cron = self.env.ref('l10n_nl_reports.cron_l10n_nl_reports_status_process')
        status_service_cron._trigger()

    def _check_sbr_certificates(self):
        cert_data = self.env.company.sudo().l10n_nl_reports_sbr_cert_id.pem_certificate
        key_data = self.env.company.sudo().l10n_nl_reports_sbr_cert_id.private_key_id.pem_key
        if not cert_data or not key_data:
            raise RedirectWarning(
                _("The certificate or the private key is missing. Please upload it in the Accounting Settings first."),
                self.env.ref('account.action_account_config').id,
                _("Go to the Accounting Settings"),
            )

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            node = arch.find(".//field[@name='can_report_be_sent']...")
            if node is not None:
                pwd_element = Element('field')
                pwd_element.set('name', 'company_id')
                pwd_element.set('invisible', '1')
                node.append(pwd_element)
        return arch, view

    def action_download_xbrl_file(self):
        options = self.env.context['options']
        options['codes_values'] = self._generate_general_codes_values(options)
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'model': self.env.context.get('model'),
                'options': json.dumps(options),
                'file_generator': 'export_tax_report_to_xbrl',
            }
        }

    def send_xbrl(self):
        # Send the XBRL file to the government with the use of a Zeep client.
        # The wsdl address points to a wsdl file on the government server.
        # It contains the definition of the 'aanleveren' function, which actually sends the message.
        options = self.env.context['options']
        self._check_sbr_certificates()
        report_handler = self.env['l10n_nl_reports.tax.report.handler']
        account_return = self.env['account.return']._get_return_from_report_options(options)
        account_return._proceed_with_submission()
        # Filter for the return company's closing move and enforce a singleton with [:1]
        closing_move = account_return and account_return.closing_move_ids.filtered(
            lambda move: move.company_id == account_return.company_id
        )[:1]
        if not self.is_test:
            if not closing_move:
                raise RedirectWarning(
                    _("No closing entry was found for the selected period. Please create one and post it before sending your report."),
                    self.env['account.return'].action_open_tax_return_view(additional_return_domain=[
                        ('date_to', '<=', options['date']['date_to']),
                        ('date_from', '>=', options['date']['date_from']),
                        ('type_id.report_id', '=', options['report_id']),
                    ]),
                    _("Create Closing Entry"),
                )
            if any(move.state == 'draft' for move in closing_move):
                raise RedirectWarning(
                    _("The closing entry for the selected period is still in draft. Please post it before sending your report."),
                    self.env['account.return'].action_open_tax_return_view(additional_return_domain=[
                        ('date_to', '<=', options['date']['date_to']),
                        ('date_from', '>=', options['date']['date_from']),
                        ('type_id.report_id', '=', options['report_id']),
                    ]),
                    _("Closing Entry"),
                )
        options['codes_values'] = self._generate_general_codes_values(options)
        xbrl_data = report_handler.export_tax_report_to_xbrl(options)
        report_file = xbrl_data['file_content']

        serv_root_cert = self.env.company._l10n_nl_get_server_root_certificate_bytes()
        certificate = base64.b64decode(self.env.company.sudo().l10n_nl_reports_sbr_cert_id.pem_certificate)
        private_key = base64.b64decode(self.env.company.sudo().l10n_nl_reports_sbr_cert_id.private_key_id.pem_key)
        try:
            with NamedTemporaryFile(delete=False) as f:
                f.write(serv_root_cert)
                f.flush()
                wsdl = 'https://' + ('preprod-' if self.is_test else '') + 'dgp2.procesinfrastructuur.nl/wus/2.0/aanleverservice/1.2?wsdl'
                service_address = 'https://' + ('wus.preproductie.digipoort.' if self.is_test else 'wus.digipoort.') + 'logius.nl/wus/2.0/aanleverservice/1.2'
                client, service = SoapClientWrapper().create_soap_client_logius(wsdl, f, certificate, private_key, serv_root_cert, service_address)
                factory = client.type_factory('ns0')
                aanleverkenmerk = wsse.utils.get_unique_id()

                response = service.aanleveren(
                    berichtsoort='Omzetbelasting',
                    aanleverkenmerk=aanleverkenmerk,
                    identiteitBelanghebbende=factory.identiteitType(nummer=self._get_sbr_identifier(options), type='BTW'),
                    rolBelanghebbende='Bedrijf',
                    berichtInhoud=factory.berichtInhoudType(mimeType='application/xml', bestandsnaam='TaxReport.xbrl', inhoud=report_file),
                    autorisatieAdres='http://geenausp.nl',
                )
                kenmerk = response.kenmerk
        except Fault as fault:
            detail_fault = fault.detail.getchildren()[0]
            raise RedirectWarning(
                message=_("The Tax Service returned the following error. Please upgrade your module and try again before submitting a support ticket.") + "\n\n" + detail_fault.find("fault:foutbeschrijving", namespaces={**fault.detail.nsmap, **detail_fault.nsmap}).text,
                action=self.env.ref('base.open_module_tree').id,
                button_text=_("Go to Apps"),
                additional_context={
                    'search_default_name': 'l10n_nl_reports_sbr',
                    'search_default_extra': True,
                },
            )
        finally:
            os.unlink(f.name)

        if not self.is_test:
            self.env.company.sudo().l10n_nl_reports_sbr_last_sent_date_to = self.date_to
            subject = _("Tax report sent")
            body = _(
                "The tax report from %(date_from)s to %(date_to)s was sent to Digipoort.%(newline)s"
                "We will post its processing status in this chatter once received.%(newline)s"
                "Discussion ID: %(id)s",
                date_from=format_date(self.env, self.date_from),
                date_to=format_date(self.env, self.date_to),
                id=kenmerk,
                newline=Markup("<br>"),
            )
            filename = f'tax_report_{self.date_to.year}_{self.date_to.month}.xbrl'
            self.env['l10n_nl_reports.sbr.status.service']._process_messages_and_statuses(
                account_return, subject, body, attachments=[(filename, report_file)], subscribe=True, status='pending',
            )

        self._additional_processing(options, kenmerk, closing_move)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Sending your report"),
                'type': 'success',
                'message': _("Your tax report is being sent to Digipoort. Check its status in the closing entry's chatter."),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _generate_general_codes_values(self, options):
        self._check_values()
        report = self.env['account.report'].browse(options['report_id'])
        sender_vat = report._get_sender_company_for_export(options).vat
        vat_identification_division = compact(sender_vat) if sender_vat else ''
        vat = report.get_vat_for_export(options)
        message_reference_supplier_vat = (self.env.company.account_representative_id.vat or vat)
        if message_reference_supplier_vat.startswith('NL'):
            message_reference_supplier_vat = compact(message_reference_supplier_vat)
        return {
            'identifier': self._get_sbr_identifier(options),
            'startDate': fields.Date.to_string(self.date_from),
            'endDate': fields.Date.to_string(self.date_to),
            'ContactInitials': self.contact_initials or '',
            'ContactPrefix': self.contact_prefix,
            'ContactSurname': self.contact_surname,
            'ContactTelephoneNumber': re.sub(r"[^\+\d]", "", self.contact_phone or ''),
            'ContactType': self.contact_type,
            'DateTimeCreation': fields.Datetime.now().strftime("%Y%m%d%H%M"),
            'MessageReferenceSupplierVAT': (message_reference_supplier_vat + '-' + str(uuid.uuid4()))[:20],
            'ProfessionalAssociationForTaxServiceProvidersName': (self.env.company.account_representative_id.name or '')[:20],
            'ProfessionalAssociationForTaxServiceProvidersOrder': self.tax_consultant_order,
            'SoftwarePackageName': 'Odoo',
            'SoftwarePackageVersion': '.'.join(self.sudo().env.ref('base.module_base').latest_version.split('.')[0:3]),
            'SoftwareVendorAccountNumber': 'swo02770',
            'TaxConsultantNumber': self.tax_consultant_number,
            'VATIdentificationNumberNLFiscalEntityDivision': vat_identification_division,
        }
