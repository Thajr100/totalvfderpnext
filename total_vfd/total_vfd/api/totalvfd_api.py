import json
import logging

import requests

from total_vfd.api.response_parser import TotalVfdResponseParser

_logger = logging.getLogger(__name__)

SANDBOX_BASE_URL = "https://testapi.totalvfd.co.tz"
PRODUCTION_BASE_URL = "https://api.totalvfd.co.tz"
SALES_ENDPOINT = "/sales"
HTTP_CREATED = 201
DEFAULT_TIMEOUT = 30
HTTP_CONFLICT = 409


class TotalVfdApiError(Exception):
    def __init__(self, message, status_code=None, response_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class TotalVfdApi:
    def __init__(self, company_name):
        self.company = company_name
        self._settings = self._load_company_settings()
        self._validate_configuration()

    def _load_company_settings(self):
        import frappe

        return frappe.get_doc("Company", self.company)

    def _validate_configuration(self):
        token = self._settings.get_password("totalvfd_bearer_token", raise_exception=False)
        if not token:
            raise TotalVfdApiError("Bearer token is not configured on Company.")
        if not self._settings.get("totalvfd_active_business"):
            raise TotalVfdApiError("Active business is not configured on Company.")
        if not self._settings.get("totalvfd_serial"):
            raise TotalVfdApiError("Serial number is not configured on Company.")

    @property
    def base_url(self):
        if self._settings.get("totalvfd_environment") == "production":
            return PRODUCTION_BASE_URL
        return SANDBOX_BASE_URL

    @property
    def endpoint(self):
        return f"{self.base_url}{SALES_ENDPOINT}"

    @staticmethod
    def _is_success_status(status_code):
        if status_code == HTTP_CREATED:
            return True
        return 200 <= status_code < 300

    def _build_headers(self):
        token = self._settings.get_password("totalvfd_bearer_token")
        return {
            "Authorization": f"Bearer {token}",
            "x-active-business": self._settings.totalvfd_active_business,
            "Content-Type": "application/json",
        }

    def send_receipt(self, payload):
        headers = self._build_headers()
        _logger.info(
            "Total VFD API request to %s for reference %s",
            self.endpoint,
            payload.get("referenceNumber"),
        )
        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
        except requests.Timeout as exc:
            raise TotalVfdApiError("Request timed out.") from exc
        except requests.ConnectionError as exc:
            raise TotalVfdApiError("Network connection failed.") from exc
        except requests.RequestException as exc:
            raise TotalVfdApiError(str(exc)) from exc

        try:
            response_body = response.json()
        except (json.JSONDecodeError, ValueError):
            response_body = {"raw": response.text}

        if self._is_success_status(response.status_code):
            return self._build_result(headers, response.status_code, response_body)

        if response.status_code == HTTP_CONFLICT:
            fiscal_payload = TotalVfdResponseParser.extract_fiscal_payload(response_body)
            if fiscal_payload:
                return self._build_result(
                    headers,
                    response.status_code,
                    fiscal_payload,
                    full_body=response_body,
                    is_duplicate=True,
                    api_message=TotalVfdResponseParser.extract_error_message(
                        response_body, response.status_code
                    ),
                )

        message = TotalVfdResponseParser.extract_error_message(
            response_body, response.status_code
        )
        raise TotalVfdApiError(
            message,
            status_code=response.status_code,
            response_body=response_body,
        )

    def _build_result(
        self,
        headers,
        status_code,
        fiscal_payload,
        full_body=None,
        is_duplicate=False,
        api_message=None,
    ):
        return {
            "headers": headers,
            "endpoint": self.endpoint,
            "status_code": status_code,
            "response": fiscal_payload,
            "full_response": full_body or fiscal_payload,
            "is_duplicate": is_duplicate,
            "api_message": api_message,
        }
