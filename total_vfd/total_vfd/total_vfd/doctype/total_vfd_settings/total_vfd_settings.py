import frappe
from frappe import _

from total_vfd.api.license_site_client import LicenseSiteClient, LicenseSiteError
from total_vfd.api.license_store import (
    apply_assign_word_response,
    get_license_dict,
    get_site_id,
    is_validation_configured,
    resolve_company,
)


class TotalVFDSettings(frappe.model.document.Document):
    def validate(self):
        if self.validation_server_url:
            self.validation_server_url = self.validation_server_url.strip().rstrip("/")

    def on_update(self):
        if not is_validation_configured():
            return
        self._sync_site_id()
        self._maybe_assign_word_on_first_config()

    def _sync_site_id(self):
        sid = get_site_id()
        if sid and self.site_id != sid:
            frappe.db.set_single_value("Total VFD Settings", "site_id", sid)

    def _maybe_assign_word_on_first_config(self):
        company = resolve_company()
        if not company:
            return
        lic = get_license_dict(company)
        if lic.get("base_word") and lic.get("status") in ("awaiting_key", "active"):
            return
        if lic.get("status") == "active":
            return
        try:
            from total_vfd.api.license_store import get_client

            data = get_client().assign_word(get_site_id(company))
            apply_assign_word_response(data, company)
        except LicenseSiteError as exc:
            frappe.msgprint(
                _("Could not assign license word from server: {0}").format(exc),
                title=_("License server"),
                indicator="orange",
            )


@frappe.whitelist()
def test_validation_connection():
    frappe.only_for(("System Manager", "Total VFD Manager"))
    doc = frappe.get_single("Total VFD Settings")
    url = (doc.validation_server_url or "").strip()
    key = doc.get_password("validation_api_key", raise_exception=False)
    if not url or not key:
        frappe.throw(_("Enter Validation Server URL and API Key first, then Save."))
    client = LicenseSiteClient(url, key)
    try:
        client.ping()
    except LicenseSiteError as exc:
        frappe.throw(_("Connection failed: {0}").format(exc))
    return {"ok": True, "message": _("Connected successfully.")}


@frappe.whitelist()
def refresh_license_word(company=None):
    """Pull or refresh license word from validation server."""
    frappe.only_for(("System Manager", "Total VFD Manager"))
    from total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license import assign_license_word

    company = resolve_company(company)
    assign_license_word(company)
    lic = get_license_dict(company)
    return {
        "ok": True,
        "base_word": lic.get("base_word"),
        "site_id": lic.get("site_id"),
        "status": lic.get("status"),
    }


@frappe.whitelist()
def check_license_now(company=None):
    """Run license check against validation server (no fiscalise)."""
    frappe.only_for(("System Manager", "Total VFD Manager"))
    from total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license import check_module_access

    company = resolve_company(company)
    check_module_access(company)
    lic = get_license_dict(company)
    warning = frappe.db.get_single_value("Total VFD Settings", "license_warning") or ""
    return {
        "ok": True,
        "status": lic.get("status"),
        "expiry_date": str(lic.get("expiry_date") or ""),
        "warning": warning,
    }
