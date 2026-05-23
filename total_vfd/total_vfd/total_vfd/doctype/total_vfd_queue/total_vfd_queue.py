import json

import frappe
from frappe.utils import now

from total_vfd.api.fiscal_service import _send_payload
from total_vfd.api.license_constants import MAX_QUEUE_RETRIES


def enqueue(document_type, document_name, company, payload, error_message):
    existing = frappe.db.get_value(
        "Total VFD Queue",
        {
            "document_type": document_type,
            "document_name": document_name,
            "status": ("in", ["Pending", "Failed", "Processing"]),
        },
        "name",
    )
    payload_text = json.dumps(payload) if isinstance(payload, dict) else payload
    values = {
        "document_type": document_type,
        "document_name": document_name,
        "company": company,
        "payload": payload_text,
        "last_error": error_message,
        "status": "Pending",
    }
    if existing:
        doc = frappe.get_doc("Total VFD Queue", existing)
        doc.update(values)
        doc.save(ignore_permissions=True)
        return doc
    doc = frappe.get_doc({"doctype": "Total VFD Queue", **values})
    doc.insert(ignore_permissions=True)
    return doc


def process_pending_queue():
    rows = frappe.get_all(
        "Total VFD Queue",
        filters={"status": ("in", ("Pending", "Failed")), "retry_count": ("<", MAX_QUEUE_RETRIES)},
        fields=["name"],
        limit=50,
        order_by="creation asc",
    )
    for row in rows:
        frappe.get_doc("Total VFD Queue", row.name).process()


class TotalVFDQueue(frappe.model.document.Document):
    def process(self):
        if self.retry_count >= MAX_QUEUE_RETRIES:
            self.status = "Failed"
            self.save(ignore_permissions=True)
            return

        if not frappe.db.exists(self.document_type, self.document_name):
            self.status = "Failed"
            self.last_error = "Source record no longer exists."
            self.save(ignore_permissions=True)
            return

        doc = frappe.get_doc(self.document_type, self.document_name)
        if not doc.get("totalvfd_fiscalise"):
            self.status = "Failed"
            self.last_error = "Fiscalisation disabled on source record."
            self.save(ignore_permissions=True)
            return

        self.status = "Processing"
        self.save(ignore_permissions=True)

        from total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license import check_module_access

        try:
            check_module_access(self.company)
        except frappe.ValidationError as exc:
            self.retry_count += 1
            self.last_error = str(exc)
            self.status = "Failed" if self.retry_count >= MAX_QUEUE_RETRIES else "Pending"
            self.save(ignore_permissions=True)
            return

        try:
            payload = json.loads(self.payload)
        except (json.JSONDecodeError, TypeError):
            self.retry_count += 1
            self.last_error = "Invalid payload in queue."
            self.status = "Failed" if self.retry_count >= MAX_QUEUE_RETRIES else "Pending"
            self.save(ignore_permissions=True)
            return

        success = _send_payload(doc, self.document_type, payload, from_queue=True)
        if success:
            self.status = "Done"
            self.last_error = None
        else:
            self.retry_count += 1
            frappe.db.set_value(
                self.document_type,
                self.document_name,
                "totalvfd_retry_count",
                self.retry_count,
                update_modified=False,
            )
            self.last_error = frappe.db.get_value(
                self.document_type, self.document_name, "totalvfd_error_message"
            )
            self.status = "Pending" if self.retry_count < MAX_QUEUE_RETRIES else "Failed"
        self.save(ignore_permissions=True)
