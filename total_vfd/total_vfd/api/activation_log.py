import frappe


def log_activation(action, license_word, expiry_date=None, renew=False, company=None):
    try:
        from total_vfd.api.license_store import get_site_id, resolve_company

        company = resolve_company(company)
        frappe.get_doc(
            {
                "doctype": "Total VFD License Activation Log",
                "action": action,
                "license_word": license_word,
                "expiry_date": expiry_date,
                "renewal": 1 if renew else 0,
                "user": frappe.session.user,
                "site_id": get_site_id(company) if company else frappe.local.site,
                "company": company,
            }
        ).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(title="Total VFD activation log failed")
