"""License state per Company + validation settings — see SETUP.md."""

import json

import frappe
from frappe import _
from frappe.utils import getdate, today

from total_vfd.api.license_constants import (
    LICENSE_STATUS_ACTIVE,
    LICENSE_STATUS_AWAITING_KEY,
    LICENSE_STATUS_EXPIRED,
    LICENSE_STATUS_INACTIVE,
    LICENSE_STATUS_REVOKED,
    LICENSE_WARNING_DAYS,
)
from total_vfd.api.license_site_client import LicenseSiteClient, LicenseSiteError


@frappe.whitelist()
def get_site_id_api(company=None) -> str:
    return get_site_id(company)


def resolve_company(company=None) -> str:
    if company:
        return company
    return frappe.defaults.get_global_default("company") or ""


def is_default_company(company: str) -> bool:
    default = frappe.defaults.get_global_default("company") or ""
    return bool(company) and company == default


def get_site_id(company=None) -> str:
    """Vendor reference: ``{site}|{company}``."""
    site = frappe.local.site or frappe.conf.get("db_name") or ""
    company = resolve_company(company)
    if company:
        return f"{site}|{company}"
    return site


def get_validation_settings():
    settings = frappe.get_single("Total VFD Settings")
    url = (settings.get("validation_server_url") or "").strip()
    key = settings.get_password("validation_api_key", raise_exception=False) or ""
    return url, key


def is_validation_configured() -> bool:
    return LicenseSiteClient.is_configured()


def require_validation_server():
    if not is_validation_configured():
        frappe.throw(
            _(
                "Complete Step 1 in Total VFD Settings first "
                "(license server address and password from your vendor), then Save."
            )
        )


def get_client() -> LicenseSiteClient:
    require_validation_server()
    return LicenseSiteClient.from_settings()


def _read_license_raw(company: str) -> str:
    if company and frappe.db.exists("Company", company):
        raw = frappe.db.get_value("Company", company, "totalvfd_license_json") or ""
        if raw:
            return raw
    if company and is_default_company(company):
        return frappe.db.get_single_value("Total VFD Settings", "license_json") or ""
    return ""


def get_license_dict(company=None) -> dict:
    company = resolve_company(company)
    raw = _read_license_raw(company) if company else ""
    if not raw and not company:
        raw = frappe.db.get_single_value("Total VFD Settings", "license_json") or ""
    if not raw:
        empty = _empty_license_dict(company)
        return empty
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data.setdefault("site_id", get_site_id(company))
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return _empty_license_dict(company)


def _empty_license_dict(company=None) -> dict:
    return {
        "site_id": get_site_id(company),
        "base_word": "",
        "activation_phrase": "",
        "license_key_hash": "",
        "status": LICENSE_STATUS_INACTIVE,
        "activation_date": "",
        "expiry_date": "",
        "integrity_seal": "",
        "vendor_activation_code_pending": "",
    }


def save_license_dict(license_data: dict, company=None):
    company = resolve_company(company)
    if not company:
        frappe.throw(_("Set a default Company before saving the module license."))

    license_data = dict(license_data)
    license_data["site_id"] = get_site_id(company)
    license_json = json.dumps(license_data, indent=2)

    frappe.db.set_value(
        "Company",
        company,
        {
            "totalvfd_license_json": license_json,
            "totalvfd_license_status": license_data.get("status") or LICENSE_STATUS_INACTIVE,
            "totalvfd_license_word": license_data.get("base_word") or "",
            "totalvfd_license_site_id": license_data.get("site_id") or get_site_id(company),
        },
        update_modified=False,
    )

    if is_default_company(company):
        frappe.db.set_single_value("Total VFD Settings", "license_json", license_json)
        frappe.db.set_single_value(
            "Total VFD Settings",
            "site_id",
            license_data.get("site_id") or get_site_id(company),
        )
        sync_license_singleton(license_data)


def sync_license_singleton(license_data: dict):
    """Mirror default-company license onto Total VFD License for legacy desk links."""
    if not frappe.db.exists("DocType", "Total VFD License"):
        return
    if not frappe.db.exists("Total VFD License", "Total VFD License"):
        doc = frappe.new_doc("Total VFD License")
        doc.name = "Total VFD License"
        doc.status = LICENSE_STATUS_INACTIVE
        doc.site_id = license_data.get("site_id") or get_site_id()
        doc.insert(ignore_permissions=True)

    lic = frappe.get_single("Total VFD License")
    lic.site_id = license_data.get("site_id") or get_site_id()
    lic.license_word = license_data.get("base_word") or ""
    lic.activation_phrase = license_data.get("activation_phrase") or ""
    lic.status = license_data.get("status") or LICENSE_STATUS_INACTIVE
    lic.expiry_date = license_data.get("expiry_date") or None
    lic.integrity_seal = license_data.get("integrity_seal") or ""
    lic.pending_vendor_activation_code = license_data.get("vendor_activation_code_pending") or ""

    if license_data.get("activation_date"):
        try:
            from frappe.utils import get_datetime

            lic.activation_date = get_datetime(license_data["activation_date"])
        except Exception:
            lic.activation_date = None

    key_hash = license_data.get("license_key_hash") or ""
    if key_hash:
        lic.set_password("license_key_hash", key_hash)
    else:
        lic.license_key_hash = ""

    _refresh_license_messages(lic)
    lic.save(ignore_permissions=True)


def build_license_api_payload(company=None) -> dict:
    lic = get_license_dict(company)
    base = lic.get("base_word") or ""
    if base and not lic.get("activation_phrase"):
        lic["activation_phrase"] = f"{base}Tanzania"
    lic["site_id"] = lic.get("site_id") or get_site_id(company)
    return lic


def _refresh_license_messages(lic):
    if lic.status == LICENSE_STATUS_AWAITING_KEY and lic.license_word:
        lic.status_message = (
            f'Your License Word is "{lic.license_word}". Tell your vendor this word only.'
        )
    elif lic.status == LICENSE_STATUS_ACTIVE and lic.expiry_date:
        lic.status_message = f"License active until {lic.expiry_date}."
        delta = (getdate(lic.expiry_date) - getdate(today())).days
        lic.days_until_expiry = delta
        lic.is_expiring_soon = 0 <= delta <= LICENSE_WARNING_DAYS
        if lic.is_expiring_soon:
            lic.warning_message = (
                f"Your Total VFD module license expires in {delta} day(s) on {lic.expiry_date}."
            )
        else:
            lic.warning_message = ""
    elif lic.status == LICENSE_STATUS_EXPIRED:
        lic.status_message = "License has expired. Renew to continue."
        lic.warning_message = ""
    else:
        lic.status_message = lic.status_message or ""
        lic.warning_message = ""
        lic.days_until_expiry = 0
        lic.is_expiring_soon = 0


def apply_assign_word_response(data: dict, company=None):
    lic = get_license_dict(company)
    lic.update(
        {
            "site_id": data.get("site_id") or get_site_id(company),
            "base_word": data.get("base_word") or "",
            "activation_phrase": data.get("activation_phrase")
            or (f"{data.get('base_word')}Tanzania" if data.get("base_word") else ""),
            "status": data.get("status", LICENSE_STATUS_AWAITING_KEY),
            "license_key_hash": "",
            "activation_date": "",
            "expiry_date": "",
            "integrity_seal": "",
            "vendor_activation_code_pending": lic.get("vendor_activation_code_pending") or "",
        }
    )
    save_license_dict(lic, company)


def apply_activate_response(api_license: dict, company=None):
    lic = get_license_dict(company)
    lic.update(
        {
            "site_id": api_license.get("site_id") or get_site_id(company),
            "base_word": api_license.get("base_word") or lic.get("base_word"),
            "activation_phrase": api_license.get("activation_phrase") or "",
            "license_key_hash": api_license.get("license_key_hash") or "",
            "status": api_license.get("status", LICENSE_STATUS_ACTIVE),
            "activation_date": api_license.get("activation_date") or "",
            "expiry_date": api_license.get("expiry_date") or "",
            "integrity_seal": api_license.get("integrity_seal") or "",
            "vendor_activation_code_pending": api_license.get("vendor_activation_code_pending") or "",
        }
    )
    save_license_dict(lic, company)
    frappe.db.set_single_value("Total VFD Settings", "license_warning", "")


def list_companies_needing_license() -> list:
    """Companies without an active module license."""
    out = []
    for row in frappe.get_all("Company", pluck="name"):
        lic = get_license_dict(row)
        if lic.get("status") != LICENSE_STATUS_ACTIVE:
            out.append({"company": row, "status": lic.get("status") or LICENSE_STATUS_INACTIVE})
    return out


def set_license_warning(message: str):
    frappe.db.set_single_value("Total VFD Settings", "license_warning", message or "")
