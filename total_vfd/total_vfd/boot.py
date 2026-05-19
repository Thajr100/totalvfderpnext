import frappe


def boot_session(bootinfo):
    if not frappe.session.user or frappe.session.user == "Guest":
        return
    if not frappe.has_role(("System Manager", "Total VFD Manager")):
        return
    try:
        if frappe.db.exists("DocType", "Total VFD Settings"):
            bootinfo.total_vfd_show_welcome = bool(
                frappe.db.get_single_value("Total VFD Settings", "show_setup_welcome")
            )
            bootinfo.total_vfd_setup_complete = bool(
                frappe.db.get_single_value("Total VFD Settings", "setup_complete")
            )
    except Exception:
        bootinfo.total_vfd_show_welcome = False
        bootinfo.total_vfd_setup_complete = False
