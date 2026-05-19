from pathlib import Path

import frappe

PRINT_FORMAT_SPECS = [
    {
        "name": "Sales Invoice - Total VFD",
        "doc_type": "Sales Invoice",
        "file": "sales_invoice_total_vfd.html",
    },
    {
        "name": "POS Invoice - Total VFD",
        "doc_type": "POS Invoice",
        "file": "pos_invoice_total_vfd.html",
    },
]


def _print_formats_dir():
    return Path(__file__).resolve().parent.parent / "print_formats"


def ensure_print_formats():
    base = _print_formats_dir()
    for spec in PRINT_FORMAT_SPECS:
        html_path = base / spec["file"]
        if not html_path.is_file():
            frappe.log_error(f"Total VFD print format template missing: {html_path}")
            continue
        html = html_path.read_text(encoding="utf-8")
        if frappe.db.exists("Print Format", spec["name"]):
            doc = frappe.get_doc("Print Format", spec["name"])
            doc.html = html
            doc.doc_type = spec["doc_type"]
            doc.module = "Total VFD"
            doc.custom_format = 1
            doc.print_format_type = "Jinja"
            doc.disabled = 0
            doc.save(ignore_permissions=True)
        else:
            frappe.get_doc(
                {
                    "doctype": "Print Format",
                    "name": spec["name"],
                    "doc_type": spec["doc_type"],
                    "module": "Total VFD",
                    "standard": "No",
                    "custom_format": 1,
                    "print_format_type": "Jinja",
                    "disabled": 0,
                    "html": html,
                }
            ).insert(ignore_permissions=True)
