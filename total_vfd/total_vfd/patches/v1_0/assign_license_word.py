import frappe


def execute():
    from total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license import assign_license_word

    assign_license_word()
    frappe.db.commit()
