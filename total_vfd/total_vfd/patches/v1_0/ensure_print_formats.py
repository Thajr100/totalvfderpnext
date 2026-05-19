import frappe


def execute():
    from total_vfd.api.print_formats import ensure_print_formats

    ensure_print_formats()
    frappe.db.commit()
