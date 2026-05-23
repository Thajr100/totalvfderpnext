import importlib.util
import logging
import sys

import frappe

_logger = logging.getLogger(__name__)

PYTHON_PACKAGES = {
    "qrcode": "qrcode",
    "PIL": "Pillow",
    "requests": "requests",
}


def _missing_python_packages():
    missing = []
    for module_name, pip_name in PYTHON_PACKAGES.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(pip_name)
    return sorted(set(missing))


def before_install():
    missing = _missing_python_packages()
    if not missing:
        return
    packages = " ".join(missing)
    frappe.throw(
        "Total VFD is missing required Python packages.\n\n"
        f"Missing: {packages}\n\n"
        "Install the app requirements in the bench environment, then install this app again:\n"
        f"    {sys.executable} -m pip install -r apps/total_vfd/requirements.txt"
    )


def _ensure_roles():
    for role_name in ("Total VFD User", "Total VFD Manager"):
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
                ignore_permissions=True
            )


def _grant_manager_to_administrators():
    for user in frappe.get_all("User", filters={"enabled": 1}, pluck="name"):
        if "Administrator" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user):
            user_doc = frappe.get_doc("User", user)
            roles = {r.role for r in user_doc.roles}
            if "Total VFD Manager" not in roles:
                user_doc.add_roles("Total VFD Manager")


def after_install():
    from total_vfd.api.print_formats import ensure_print_formats
    from total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license import assign_license_word

    _ensure_roles()
    ensure_print_formats()
    from total_vfd.api.license_store import get_site_id, is_validation_configured

    frappe.db.set_single_value("Total VFD Settings", "site_id", get_site_id())
    if is_validation_configured():
        try:
            assign_license_word()
        except Exception as exc:
            _logger.warning("Total VFD assign-word on install skipped: %s", exc)
    frappe.db.set_single_value("Total VFD Settings", "setup_complete", 0)
    frappe.db.set_single_value("Total VFD Settings", "show_setup_welcome", 1)
    _grant_manager_to_administrators()
    _logger.info(
        "Total VFD installed. Open Total VFD Settings and follow the setup checklist (see SETUP.md)."
    )
