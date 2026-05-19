import frappe
from frappe import _
from frappe.utils import getdate, today

from total_vfd.api.license_constants import (
    LICENSE_STATUS_ACTIVE,
    LICENSE_STATUS_AWAITING_KEY,
    LICENSE_STATUS_EXPIRED,
    LICENSE_STATUS_INACTIVE,
    LICENSE_STATUS_REVOKED,
)
from total_vfd.api.license_site_client import LicenseSiteError
from total_vfd.api.license_store import (
    apply_activate_response,
    apply_assign_word_response,
    build_license_api_payload,
    get_client,
    get_license_dict,
    get_site_id,
    is_validation_configured,
    require_validation_server,
    resolve_company,
    save_license_dict,
    set_license_warning,
    sync_license_singleton,
)


def get_singleton():
    company = resolve_company()
    if not frappe.db.exists("Total VFD License", "Total VFD License"):
        doc = frappe.new_doc("Total VFD License")
        doc.name = "Total VFD License"
        doc.status = LICENSE_STATUS_INACTIVE
        doc.site_id = get_site_id(company)
        doc.insert(ignore_permissions=True)
    sync_license_singleton(get_license_dict(company))
    return frappe.get_single("Total VFD License")


def assign_license_word(company=None):
    require_validation_server()
    company = resolve_company(company)
    if not company:
        frappe.throw(_("Set a default Company before assigning a license word."))

    lic = get_license_dict(company)
    if lic.get("status") == LICENSE_STATUS_ACTIVE:
        sync_license_singleton(lic)
        return get_singleton()
    if lic.get("base_word") and lic.get("status") == LICENSE_STATUS_AWAITING_KEY:
        sync_license_singleton(lic)
        return get_singleton()

    site_id = get_site_id(company)
    try:
        data = get_client().assign_word(site_id)
    except LicenseSiteError as exc:
        frappe.throw(str(exc))

    apply_assign_word_response(data, company)
    return get_singleton()


def check_module_access(company=None):
    require_validation_server()
    company = resolve_company(company)
    if not company:
        frappe.throw(_("Set a default Company before fiscalising."))

    lic = get_license_dict(company)
    if not lic.get("base_word"):
        assign_license_word(company)
        lic = get_license_dict(company)

    if lic.get("status") == LICENSE_STATUS_ACTIVE:
        try:
            result = get_client().check(build_license_api_payload(company))
            set_license_warning(result.get("warning") or "")
            sync_license_singleton(get_license_dict(company))
            return get_singleton()
        except LicenseSiteError as exc:
            _sync_expired_from_expiry(lic, company)
            frappe.throw(
                _("{0}\n\nOpen Total VFD Settings and complete the setup checklist.").format(exc)
            )

    messages = {
        LICENSE_STATUS_AWAITING_KEY: _(
            'For {1}: email your vendor (step 2), then enter their code and key (step 3). Your code word is "{0}".'
        ).format(lic.get("base_word"), company),
        LICENSE_STATUS_INACTIVE: _("Complete the setup checklist in Total VFD Settings."),
        LICENSE_STATUS_EXPIRED: _(
            "License for {0} has expired. Get a new code and key from your vendor, then activate again."
        ).format(company),
        LICENSE_STATUS_REVOKED: _("License for {0} was revoked. Contact your vendor.").format(company),
    }
    frappe.throw(messages.get(lic.get("status"), messages[LICENSE_STATUS_INACTIVE]))


def _sync_expired_from_expiry(lic, company):
    expiry = lic.get("expiry_date")
    if expiry and getdate(expiry) < getdate(today()):
        lic["status"] = LICENSE_STATUS_EXPIRED
        save_license_dict(lic, company)


def is_license_active(company=None):
    try:
        check_module_access(company)
        return True
    except frappe.ValidationError:
        return False


def cron_check_license():
    if not is_validation_configured():
        return
    for row in frappe.get_all("Company", pluck="name"):
        lic = get_license_dict(row)
        if lic.get("status") != LICENSE_STATUS_ACTIVE:
            continue
        try:
            result = get_client().check(build_license_api_payload(row))
            if is_default_company(row):
                set_license_warning(result.get("warning") or "")
        except LicenseSiteError:
            if resolve_company() == row or is_default_company(row):
                set_license_warning("")
            _sync_expired_from_expiry(lic, row)
        if is_default_company(row):
            sync_license_singleton(get_license_dict(row))


def is_default_company(company):
    from total_vfd.api.license_store import is_default_company as _is_default

    return _is_default(company)


@frappe.whitelist()
def get_vendor_message(company=None):
    require_validation_server()
    company = resolve_company(company)
    lic = get_license_dict(company)
    if not lic.get("base_word"):
        assign_license_word(company)
        lic = get_license_dict(company)
    return "\n".join(
        [
            "Hello,",
            "",
            "Please activate Total VFD for our ERPNext system.",
            "",
            f"Company name in ERPNext: {company}",
            f"Our activation code word: {lic.get('base_word')}",
            f"Reference number for your system: {lic.get('site_id') or get_site_id(company)}",
            "",
            "Please reply with our short activation code and license key.",
            "",
            "Thank you.",
        ]
    )


@frappe.whitelist()
def register_vendor_code(vendor_activation_code, company=None):
    if not vendor_activation_code or not str(vendor_activation_code).strip():
        frappe.throw(_("Paste the Vendor Activation Code from your vendor email."))
    company = resolve_company(company)
    lic = get_license_dict(company)
    lic["vendor_activation_code_pending"] = str(vendor_activation_code).strip()
    save_license_dict(lic, company)
    return {"ok": True}


@frappe.whitelist()
def activate_license(license_key, vendor_activation_code=None, renew=0, company=None):
    require_validation_server()
    company = resolve_company(company)
    lic = get_license_dict(company)
    if lic.get("status") == LICENSE_STATUS_REVOKED:
        frappe.throw(_("This license has been revoked and cannot be activated."))

    if not lic.get("base_word"):
        assign_license_word(company)
        lic = get_license_dict(company)

    renew = int(renew or 0)
    site_id = get_site_id(company)
    vendor_code = (vendor_activation_code or lic.get("vendor_activation_code_pending") or "").strip() or None

    if not renew and not vendor_code:
        frappe.throw(_("Vendor Activation Code is required for activation."))

    try:
        result = get_client().activate(
            site_id,
            license_key,
            build_license_api_payload(company),
            vendor_code=None if renew else vendor_code,
        )
    except LicenseSiteError as exc:
        frappe.throw(str(exc))

    api_license = result.get("license")
    if not api_license:
        frappe.throw(_("License server returned an empty license."))

    apply_activate_response(api_license, company)

    from total_vfd.api.activation_log import log_activation

    log_activation(
        "renewed" if renew else "activated",
        api_license.get("base_word"),
        api_license.get("expiry_date"),
        renew=bool(renew),
        company=company,
    )

    lic_doc = get_singleton()
    return {
        "status": lic_doc.status,
        "expiry_date": str(lic_doc.expiry_date or ""),
        "days_until_expiry": lic_doc.days_until_expiry,
        "default_company": company,
        "company": company,
    }


@frappe.whitelist()
def revoke_license(company=None):
    frappe.only_for(("System Manager", "Total VFD Manager"))
    company = resolve_company(company)
    lic = get_license_dict(company)
    if lic.get("status") == LICENSE_STATUS_REVOKED:
        frappe.throw(_("License is already revoked."))
    lic["status"] = LICENSE_STATUS_REVOKED
    save_license_dict(lic, company)
    from total_vfd.api.activation_log import log_activation

    log_activation("revoked", lic.get("base_word"), company=company)
    return {"status": LICENSE_STATUS_REVOKED, "company": company}


class TotalVFDLicense(frappe.model.document.Document):
    def validate(self):
        company = resolve_company()
        sync_license_singleton(get_license_dict(company))
