import frappe


def execute():
    from total_vfd.api.print_formats import ensure_print_formats
    from total_vfd.install import _ensure_roles, _grant_manager_to_administrators
    from total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license import assign_license_word

    _ensure_roles()
    assign_license_word()
    ensure_print_formats()
    _grant_manager_to_administrators()
    frappe.db.set_single_value("Total VFD Settings", "show_setup_welcome", 1)
    frappe.db.commit()
