"""Copy site-level license_json to default Company; enable per-company fields."""

import json

import frappe

from total_vfd.api.license_store import get_site_id, resolve_company, save_license_dict


def execute():
    raw = frappe.db.get_single_value("Total VFD Settings", "license_json") or ""
    company = resolve_company()
    if not company or not raw:
        return
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return
    if not isinstance(data, dict) or not data.get("base_word"):
        return
    data.setdefault("site_id", get_site_id(company))
    if not frappe.db.get_value("Company", company, "totalvfd_license_json"):
        save_license_dict(data, company)
