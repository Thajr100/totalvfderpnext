"""Migrate local license fields to license_json and set site_id format."""

import json

import frappe

from total_vfd.api.license_store import get_site_id, save_license_dict


def execute():
    if not frappe.db.exists("DocType", "Total VFD Settings"):
        return

    lic_data = {}
    if frappe.db.exists("Total VFD License", "Total VFD License"):
        lic = frappe.get_single("Total VFD License")
        key_hash = ""
        try:
            key_hash = lic.get_password("license_key_hash") or ""
        except Exception:
            pass
        lic_data = {
            "site_id": lic.site_id or get_site_id(),
            "base_word": lic.license_word or "",
            "activation_phrase": lic.activation_phrase or "",
            "license_key_hash": key_hash,
            "status": lic.status or "inactive",
            "activation_date": str(lic.activation_date or "")[:10] if lic.activation_date else "",
            "expiry_date": str(lic.expiry_date or "") if lic.expiry_date else "",
            "integrity_seal": lic.integrity_seal or "",
            "vendor_activation_code_pending": lic.pending_vendor_activation_code or "",
        }

    existing = frappe.db.get_single_value("Total VFD Settings", "license_json")
    if not existing and lic_data.get("base_word"):
        frappe.db.set_single_value(
            "Total VFD Settings",
            "license_json",
            json.dumps(lic_data, indent=2),
        )

    frappe.db.set_single_value("Total VFD Settings", "site_id", get_site_id())
    frappe.db.commit()
