import json
from datetime import datetime, timedelta, timezone

import requests

from odoo import api, fields, models


class AccessToken:
    token: str
    expires_at: datetime
    token_type: str

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


class SyncRecord(models.Model):
    _name = "xx.sync.record"
    _description = "Sync record"

    _token_object = None
    _batch_size = 50

    user_login = fields.Char(required=True)
    timestamp = fields.Datetime(required=True, default=fields.Datetime.now)
    model_name = fields.Char(required=True)
    endpoint = fields.Char(default="")
    method = fields.Char(required=True, default="POST")
    content = fields.Text(required=True)
    synced = fields.Boolean(default=False)
    sync_date = fields.Datetime()
    response_message = fields.Text()

    @api.model
    def queue(cls, env, *, model, payload, endpoint, method):
        if isinstance(payload, dict):
            payload = [payload]

        return env["xx.sync.record"].create(
            {
                "user_login": env.user.login,
                "model_name": model,
                "endpoint": endpoint,
                "method": method,
                "content": json.dumps(payload, indent=4),
                "synced": False,
            }
        )

    def process_unsynced_records(self):
        last_id = 0
        batch_size = self.__class__._batch_size

        while True:
            records = self.search(
                [
                    ("synced", "=", False),
                    ("id", ">", last_id),
                ],
                limit=batch_size,
                order="id",
            )

            if not records:
                break

            records.with_delay()._process_batch()

            last_id = records[-1].id

    def _process_batch(self):
        for record in self:
            record._process_single_record()

    def _process_single_record(self):
        self.ensure_one()

        if not self.synced:
            base_url = self.env["ir.config_parameter"].sudo().get_param("xx_horizon.pas_base_url")

            try:
                api_url = f"{base_url}/{self.endpoint}"
                payload = json.loads(self.content)

                for item in payload:
                    item.update(
                        {
                            "Sync_ID": self.id,
                            "ModifyUser": self.user_login,
                            "ModifyDate": self.timestamp.date().isoformat()
                            if self.timestamp
                            else None,
                            "ModifyTime": self.timestamp.time().isoformat()
                            if self.timestamp
                            else None,
                        }
                    )

                payload = {"data": payload}

                if (
                    self.__class__._token_object is None
                    or self.__class__._token_object.is_expired()
                ):
                    self.__class__._token_object = self.get_pas_token()

                headers = {
                    "Authorization": f"Bearer {self.__class__._token_object.token}",
                }
                if self.method == "POST":
                    response = requests.post(api_url, headers=headers, json=payload, timeout=10)
                elif self.method == "PUT":
                    response = requests.put(api_url, headers=headers, json=payload, timeout=10)
                elif self.method == "DELETE":
                    response = requests.delete(api_url, headers=headers, json=payload, timeout=10)
                else:
                    raise ValueError(f"Unsupported method: {self.method}")

                self.write(
                    {
                        "response_message": f"{response.status_code}: {response.text}",
                    }
                )

                if response.status_code == 200:
                    self.write(
                        {
                            "synced": True,
                            "sync_date": fields.Datetime.now(),
                        }
                    )
                    if not self.env.context.get("skip_commit", False):
                        self.env.cr.commit()  # pylint: disable=invalid-commit

            except Exception as e:
                self.write({"response_message": f"Exception: {str(e)}"})

    def parse_token_response(self, response_json: dict) -> AccessToken:
        expires_in = int(response_json["expires_in"])

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        access_token = AccessToken()
        access_token.token = response_json["access_token"]
        access_token.token_type = response_json.get("token_type", "Bearer")
        access_token.expires_at = expires_at

        return access_token

    def get_pas_token(self):
        keys = [
            "xx_horizon.auth_tenant_id",
            "xx_horizon.auth_url",
            "xx_horizon.auth_client_id",
            "xx_horizon.auth_scope",
            "xx_horizon.auth_grant_type",
            "xx_horizon.auth_client_secret",
        ]
        values = map(lambda k: self.env["ir.config_parameter"].sudo().get_param(k), keys)
        params = dict(zip(keys, values, strict=False))

        tenant = params["xx_horizon.auth_tenant_id"]
        url = f"{params['xx_horizon.auth_url']}/{tenant}/oauth2/v2.0/token"

        data = {
            "client_id": params["xx_horizon.auth_client_id"],
            "scope": params["xx_horizon.auth_scope"],
            "grant_type": params["xx_horizon.auth_grant_type"],
            "client_secret": params["xx_horizon.auth_client_secret"],
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        response = requests.post(url, data=data, headers=headers, timeout=10)
        if response.status_code != 200:
            raise ValueError(f"Failed to obtain token: {response.status_code} - {response.text}")

        token_obj = self.parse_token_response(response.json())

        return token_obj
