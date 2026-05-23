import frappe
from frappe import _

from total_vfd.api.license_store import (
    get_license_dict,
    get_site_id,
    get_validation_settings,
    is_validation_configured,
    list_companies_needing_license,
    resolve_company,
)


def has_app_permission():
    return frappe.has_role(("System Manager", "Total VFD Manager", "Total VFD User"))


def _license_status_for_company(company):
    lic = get_license_dict(company)
    return {
        "word_assigned": bool(lic.get("base_word")),
        "vendor_code_saved": bool(lic.get("vendor_activation_code_pending"))
        or lic.get("status") == "active",
        "license_active": lic.get("status") == "active",
        "license_status": lic.get("status"),
        "license_word": lic.get("base_word"),
        "activation_phrase": lic.get("activation_phrase") or "",
        "site_id": lic.get("site_id") or get_site_id(company),
        "expiry_date": str(lic.get("expiry_date") or ""),
        "days_until_expiry": _days_until_expiry(lic.get("expiry_date")),
    }


@frappe.whitelist()
def get_setup_status(company=None):
    company = resolve_company(company)
    lic_info = _license_status_for_company(company) if company else {}
    api_ok = False
    if company and frappe.db.exists("Company", company):
        comp = frappe.get_doc("Company", company)
        api_ok = bool(
            comp.get_password("totalvfd_bearer_token", raise_exception=False)
            and comp.get("totalvfd_active_business")
            and comp.get("totalvfd_serial")
        )

    other_companies = list_companies_needing_license()
    multi_company = len(frappe.get_all("Company", pluck="name")) > 1

    return {
        "validation_configured": is_validation_configured(),
        "company": company,
        "multi_company": multi_company,
        "companies_needing_license": other_companies,
        **lic_info,
        "license_warning": frappe.db.get_single_value("Total VFD Settings", "license_warning") or "",
        "api_configured": api_ok,
        "default_company": company,
        "setup_complete": bool(frappe.db.get_single_value("Total VFD Settings", "setup_complete")),
        "fiscalisation_blocked": not is_validation_configured()
        or lic_info.get("license_status") != "active",
    }


def _days_until_expiry(expiry_date):
    if not expiry_date:
        return 0
    from frappe.utils import getdate, today

    return (getdate(expiry_date) - getdate(today())).days


@frappe.whitelist()
def mark_setup_complete():
    frappe.only_for(("System Manager", "Total VFD Manager"))
    frappe.db.set_single_value("Total VFD Settings", "setup_complete", 1)
    return {"ok": True}


def company_updated(doc, method=None):
    frappe.db.set_single_value("Total VFD Settings", "site_id", get_site_id(doc.name))
    status = get_setup_status(doc.name)
    if status.get("license_active") and status.get("api_configured"):
        frappe.db.set_single_value("Total VFD Settings", "setup_complete", 1)


@frappe.whitelist()
def get_license_banner(company=None):
    company = resolve_company(company)
    status = get_setup_status(company)
    if not status["validation_configured"]:
        return {
            "level": "orange",
            "message": _(
                "Open Total VFD Settings and complete Step 1 (license server address and password), then Save."
            ),
        }
    if status["license_warning"]:
        return {"level": "warning", "message": status["license_warning"]}
    if status["fiscalisation_blocked"]:
        label = company or _("this company")
        return {
            "level": "orange",
            "message": _(
                "Fiscalisation is disabled for {0} until the module license is active. "
                "Open Total VFD Settings."
            ).format(label),
        }
    return None


@frappe.whitelist()
def get_guided_steps(company=None):
    company = resolve_company(company)
    s = get_setup_status(company)
    steps = [
        {
            "id": "validation_server",
            "number": 1,
            "title": _("Link to your vendor"),
            "help": _("Paste the license server address and password above, Save, then Test link to vendor."),
            "done": s["validation_configured"],
            "action": "validation",
        },
        {
            "id": "vendor_message",
            "number": 2,
            "title": _("Email your vendor"),
            "help": _("Copy our ready-made email. Your vendor will send back a short code and a license key."),
            "done": s["word_assigned"],
            "action": "copy_vendor",
        },
        {
            "id": "activate",
            "number": 3,
            "title": _("Turn on your license"),
            "help": _("Enter the short code and license key from your vendor's email."),
            "done": s["license_active"],
            "action": "activate",
        },
        {
            "id": "api",
            "number": 4,
            "title": _("Connect your fiscal device"),
            "help": _("On Company → Total VFD: portal token, business ID, and device serial (use test mode first)."),
            "done": s["api_configured"],
            "action": "open_company",
        },
        {
            "id": "pos",
            "number": 5,
            "title": _("Till / POS (optional)"),
            "help": _("Only if you use Point of Sale."),
            "done": _pos_configured(),
            "optional": True,
            "action": "open_pos_profile",
        },
        {
            "id": "test",
            "number": 6,
            "title": _("Try a test invoice"),
            "help": _("Tick Fiscalise on a Sales Invoice and submit while still in test mode."),
            "done": s["setup_complete"],
            "action": "open_sales_invoice",
        },
    ]
    required = [st for st in steps if not st.get("optional")]
    done_count = sum(1 for step in required if step["done"])
    progress = int(100 * done_count / max(len(required), 1))
    return {
        "status": s,
        "steps": steps,
        "progress_percent": min(progress, 100),
        "all_ready": s["validation_configured"] and s["license_active"] and s["api_configured"],
    }


def _pos_configured():
    rows = frappe.get_all(
        "POS Profile",
        filters={"totalvfd_fiscalise_by_default": 1},
        limit=1,
    )
    return bool(rows)


@frappe.whitelist()
def dismiss_setup_welcome():
    frappe.only_for(("System Manager", "Total VFD Manager"))
    frappe.db.set_single_value("Total VFD Settings", "show_setup_welcome", 0)
    return {"ok": True}


@frappe.whitelist()
def get_it_request_message():
    """Plain-text note the customer can send to IT / integrator."""
    company = resolve_company()
    site = frappe.local.site or ""
    lines = [
        "Please set up Total VFD on our ERPNext system.",
        "",
        f"ERPNext site: {site}",
        f"Company in ERPNext: {company or '(set default company)'}",
        "",
        "We need from you:",
        "1) License server web address",
        "2) License password for that server",
        "3) Confirmation the license server is running",
        "",
        "After that we will complete setup inside ERPNext → Total VFD Settings.",
    ]
    return "\n".join(lines)
