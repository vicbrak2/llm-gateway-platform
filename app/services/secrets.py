from __future__ import annotations

import os


class SecretResolver:
    def __init__(
        self,
        infisical_enabled: bool = False,
        host: str | None = None,
        token: str | None = None,
        project_id: str | None = None,
        environment_slug: str | None = None,
        secret_path: str | None = None,
    ) -> None:
        self.infisical_enabled = infisical_enabled
        self.host = host
        self.token = token
        self.project_id = project_id
        self.environment_slug = environment_slug
        self.secret_path = secret_path
        self._client = None

    def get(self, name: str) -> str | None:
        value = os.getenv(name)
        if value:
            return value
        if not self.infisical_enabled:
            return None
        return self._get_from_infisical(name)

    def _get_from_infisical(self, name: str) -> str | None:
        try:
            from infisical_sdk import InfisicalSDKClient
        except Exception:
            return None

        if not all([self.host, self.token, self.project_id, self.environment_slug]):
            return None

        if self._client is None:
            self._client = InfisicalSDKClient(host=self.host)
            self._client.auth.universal_auth.login(client_secret=self.token)

        try:
            secret = self._client.secrets.get_by_name(
                secret_name=name,
                project_id=self.project_id,
                environment_slug=self.environment_slug,
                secret_path=self.secret_path or "/",
            )
            return getattr(secret, "secretValue", None)
        except Exception:
            return None
