import frappe


def apply_pos_fiscalise_default(doc, method=None):
    """Enable fiscalisation on new POS invoices when the POS Profile default is set."""
    if doc.get("totalvfd_fiscalise"):
        return
    if not doc.get("pos_profile"):
        return
    if doc.docstatus != 0:
        return

    default = frappe.db.get_value(
        "POS Profile",
        doc.pos_profile,
        "totalvfd_fiscalise_by_default",
    )
    if default:
        doc.totalvfd_fiscalise = 1


def sync_pos_profile_print_format(doc, method=None):
    """Set native POS Profile print_format when fiscal receipt printing is enabled."""
    if not doc.get("totalvfd_use_fiscal_print_format"):
        return
    if frappe.db.exists("Print Format", "POS Invoice - Total VFD"):
        doc.print_format = "POS Invoice - Total VFD"


def apply_sales_fiscalise_default(doc, method=None):
    """Optional company-level default for Sales Invoice fiscalisation."""
    if doc.get("totalvfd_fiscalise") or doc.is_return:
        return
    if not doc.get("company"):
        return
    if doc.docstatus != 0:
        return

    default = frappe.db.get_value(
        "Company",
        doc.company,
        "totalvfd_fiscalise_sales_by_default",
    )
    if default:
        doc.totalvfd_fiscalise = 1
