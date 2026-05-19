import importlib.util
import logging
import subprocess
import sys

import frappe

_logger = logging.getLogger(__name__)

PYTHON_PACKAGES = {
    "qrcode": "qrcode",
    "PIL": "Pillow",
    "requests": "requests",
}

PIP_INSTALL_TIMEOUT = 300


def _missing_python_packages():
    missing = []
    for module_name, pip_name in PYTHON_PACKAGES.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(pip_name)
    return sorted(set(missing))


def _pip_install(packages):
    if not packages:
        return
    base_cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-warn-script-location",
    ]
    attempts = [base_cmd + packages, base_cmd + ["--user"] + packages]
    last_error = None
    for cmd in attempts:
        try:
            _logger.info("Total VFD: installing Python packages: %s", " ".join(packages))
            subprocess.check_call(
                cmd,
                timeout=PIP_INSTALL_TIMEOUT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else str(exc)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            last_error = str(exc)
    raise RuntimeError(last_error or "pip install failed")


def before_install():
    missing = _missing_python_packages()
    if not missing:
        return
    _logger.info(
        "Total VFD: missing Python packages %s — attempting automatic install.",
        ", ".join(missing),
    )
    try:
        _pip_install(missing)
    except RuntimeError as exc:
        packages = " ".join(missing)
        frappe.throw(
            "Total VFD could not install required Python packages automatically.\n\n"
            f"Missing: {packages}\n\n"
            f"Error: {exc}\n\n"
            "Ask your administrator to run on the bench environment:\n"
            f"    {sys.executable} -m pip install {packages}\n\n"
            "Then install this app again."
        )
    importlib.invalidate_caches()
    still_missing = _missing_python_packages()
    if still_missing:
        packages = " ".join(still_missing)
        frappe.throw(
            "Total VFD installed Python packages but they are still not available.\n\n"
            f"Missing: {packages}\n\n"
            f"Run: bench restart\n"
            f"Then: {sys.executable} -m pip install {packages}"
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
