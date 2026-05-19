"""Unit tests for license_site client (mocked HTTP)."""

import sys
import unittest
from unittest.mock import MagicMock, patch

# Bench not required for client unit tests
sys.modules.setdefault("frappe", MagicMock())
sys.modules["frappe"].ValidationError = Exception
sys.modules["frappe"]._ = lambda x, *a, **k: x

from total_vfd.api.license_site_client import LicenseSiteClient, LicenseSiteError


class TestLicenseSiteClient(unittest.TestCase):
    def test_api_prefix_appends_v1(self):
        client = LicenseSiteClient("https://licenses.example.com", "secret-key")
        self.assertEqual(client.api_prefix(), "https://licenses.example.com/api/v1")

    def test_api_prefix_when_url_already_has_v1(self):
        client = LicenseSiteClient("https://licenses.example.com/api/v1", "secret-key")
        self.assertEqual(client.api_prefix(), "https://licenses.example.com/api/v1")

    @patch("total_vfd.api.license_site_client.requests.post")
    def test_check_raises_on_not_ok(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=403,
            json=lambda: {"ok": False, "error": "License expired"},
            text="",
            reason="Forbidden",
        )
        client = LicenseSiteClient("https://licenses.example.com", "key")
        with self.assertRaises(LicenseSiteError):
            client.check({"site_id": "site|CO", "status": "active"})

    @patch("total_vfd.api.license_site_client.requests.post")
    def test_assign_word_returns_json(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"site_id": "x|Y", "base_word": "Mauzo", "status": "awaiting_key"},
            text="",
            reason="OK",
        )
        client = LicenseSiteClient("https://licenses.example.com", "key")
        data = client.assign_word("x|Y")
        self.assertEqual(data["base_word"], "Mauzo")


if __name__ == "__main__":
    unittest.main()
