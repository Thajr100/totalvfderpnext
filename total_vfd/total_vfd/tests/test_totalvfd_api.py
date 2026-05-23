"""Unit tests for Total VFD fiscal API client."""

import unittest

from total_vfd.api.totalvfd_api import TotalVfdApi


class _Settings:
    def __init__(self, environment="sandbox"):
        self.environment = environment

    def get(self, fieldname):
        if fieldname == "totalvfd_environment":
            return self.environment
        return None


class TestTotalVfdApi(unittest.TestCase):
    def test_endpoint_uses_sales_path(self):
        client = object.__new__(TotalVfdApi)
        client.company = "Test Company"
        client._settings = _Settings()
        self.assertEqual(client.endpoint, "https://testapi.totalvfd.co.tz/sales")

    def test_created_status_is_success(self):
        self.assertTrue(TotalVfdApi._is_success_status(201))
        self.assertTrue(TotalVfdApi._is_success_status(200))
        self.assertFalse(TotalVfdApi._is_success_status(409))


if __name__ == "__main__":
    unittest.main()
