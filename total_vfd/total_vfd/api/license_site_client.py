"""HTTP client for license validation server API."""

import logging

import frappe
import requests
from frappe import _

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
PLACEHOLDER_URLS = ("", "https://licenses.example.com")
PLACEHOLDER_KEYS = ("", "change-me-validator-api-key")


class LicenseSiteError(frappe.ValidationError):
    def __init__(self, message, http_status=None):
        super().__init__(message)
        self.http_status = http_status


class LicenseSiteClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = (base_url or "").strip().rstrip("/")
        self.api_key = (api_key or "").strip()
        if not self.base_url:
            raise LicenseSiteError(_("License validation server URL is not configured."))
        if not self.api_key:
            raise LicenseSiteError(_("License validation API key is not configured."))

    @classmethod
    def from_settings(cls):
        from total_vfd.api.license_store import get_validation_settings

        url, key = get_validation_settings()
        return cls(url, key)

    @classmethod
    def is_configured(cls) -> bool:
        from total_vfd.api.license_store import get_validation_settings

        url, key = get_validation_settings()
        if not url or not key or url in PLACEHOLDER_URLS or key in PLACEHOLDER_KEYS:
            return False
        return True

    def api_prefix(self) -> str:
        if self.base_url.endswith("/api/v1"):
            return self.base_url
        return f"{self.base_url}/api/v1"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _post(self, path: str, payload: dict) -> dict:
        path = path if path.startswith("/") else f"/{path}"
        url = f"{self.api_prefix()}{path}"
        try:
            response = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
        except requests.Timeout as exc:
            raise LicenseSiteError(
                _("License validation server timed out. Check the server URL and network.")
            ) from exc
        except requests.ConnectionError as exc:
            raise LicenseSiteError(
                _("Cannot reach the license validation server. Check the URL and HTTPS certificate.")
            ) from exc
        except requests.RequestException as exc:
            raise LicenseSiteError(str(exc)) from exc

        try:
            data = response.json()
        except ValueError:
            data = {"ok": False, "error": response.text or response.reason}

        if not isinstance(data, dict):
            raise LicenseSiteError(_("Invalid response from license validation server."))

        if response.status_code == 401:
            raise LicenseSiteError(
                _("License validation API key was rejected (401). Check Total VFD Settings."),
                http_status=401,
            )
        if response.status_code == 503:
            raise LicenseSiteError(
                data.get("error") or _("License validation API is disabled on the server."),
                http_status=503,
            )
        if response.status_code >= 400 or (data.get("ok") is False and "valid" not in data):
            message = data.get("error") or data.get("message") or f"HTTP {response.status_code}"
            raise LicenseSiteError(message, http_status=response.status_code)

        return data

    def assign_word(self, site_id: str) -> dict:
        return self._post("/license/assign-word", {"site_id": site_id})

    def activate(self, site_id: str, license_key: str, license_payload: dict, vendor_code=None) -> dict:
        body = {
            "site_id": site_id,
            "license_key": license_key,
            "license": license_payload,
        }
        if vendor_code:
            body["x"] = vendor_code
        return self._post("/license/activate", body)

    def check(self, license_payload: dict) -> dict:
        data = self._post("/license/check", license_payload)
        if data.get("ok") is not True:
            raise LicenseSiteError(data.get("error") or _("License check failed."), http_status=403)
        return data

    def ping(self) -> dict:
        return self._post("/ping", {})

    def health(self) -> bool:
        url = f"{self.base_url}/api/health"
        if self.base_url.endswith("/api/v1"):
            url = self.base_url.replace("/api/v1", "/api/health")
        try:
            return requests.get(url, timeout=10).status_code == 200
        except requests.RequestException:
            return False
