import json
import logging

import frappe
from frappe import _

from total_vfd.api.license_constants import MAX_QUEUE_RETRIES
from total_vfd.api.payload_builder import PayloadBuilder
from total_vfd.api.qr_generator import QrGenerator
from total_vfd.api.response_parser import TotalVfdResponseParser
from total_vfd.api.totalvfd_api import TotalVfdApi, TotalVfdApiError

_logger = logging.getLogger(__name__)


def validate_sales_fiscalise_license(doc, method=None):
    """Block Sales Invoice submit when fiscalise is on but module license is not active."""
    if not doc.get("totalvfd_fiscalise") or doc.is_return:
        return
    from total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license import check_module_access

    check_module_access(doc.company)


def fiscalise_sales_invoice(doc, method=None):
    if not doc.get("totalvfd_fiscalise"):
        return
    if doc.is_return:
        return
    if doc.get("totalvfd_fiscal_status") == "Success" and doc.get("totalvfd_sent"):
        return
    _fiscalise_document(doc, "Sales Invoice")


def fiscalise_pos_invoice(doc, method=None):
    if not doc.get("totalvfd_fiscalise"):
        return
    if doc.get("totalvfd_fiscal_status") == "Success" and doc.get("totalvfd_sent"):
        return
    _fiscalise_document(doc, "POS Invoice")


def _fiscalise_document(doc, doctype):
    from total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license import check_module_access

    try:
        check_module_access(doc.company)
    except frappe.ValidationError as exc:
        _mark_failed(doc, doctype, str(exc))
        return

    try:
        builder = PayloadBuilder(doc.company)
        if doctype == "Sales Invoice":
            payload = builder.build_from_sales_invoice(doc)
        else:
            payload = builder.build_from_pos_invoice(doc)
    except Exception as exc:
        _logger.exception("Payload build failed for %s %s", doctype, doc.name)
        _mark_failed(doc, doctype, str(exc))
        return

    _send_payload(doc, doctype, payload, from_queue=False)


def _send_payload(doc, doctype, payload, from_queue=False):
    from total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license import check_module_access

    check_module_access(doc.company)
    payload_text = json.dumps(payload, indent=2, default=str)
    frappe.db.set_value(
        doctype,
        doc.name,
        {
            "totalvfd_fiscal_status": "Pending",
            "totalvfd_payload": payload_text,
            "totalvfd_error_message": None,
            "totalvfd_api_message": None,
        },
        update_modified=False,
    )

    api_client = None
    try:
        api_client = TotalVfdApi(doc.company)
        result = api_client.send_receipt(payload)
    except TotalVfdApiError as exc:
        endpoint = api_client.endpoint if api_client else ""
        _mark_failed(
            doc,
            doctype,
            str(exc),
            payload=payload,
            log_values={
                "endpoint": endpoint,
                "response": exc.response_body,
                "http_status": exc.status_code,
            },
        )
        return False
    except Exception as exc:
        _logger.exception("Unexpected Total VFD error for %s %s", doctype, doc.name)
        _mark_failed(doc, doctype, str(exc), payload=payload)
        return False

    fiscal_body = result.get("response") or {}
    full_response = result.get("full_response") or fiscal_body
    _apply_success(
        doc,
        doctype,
        fiscal_body,
        full_response=full_response,
        api_message=result.get("api_message"),
        is_duplicate=result.get("is_duplicate"),
    )
    _create_log(
        doc,
        doctype,
        name=payload.get("referenceNumber", doc.name),
        status="Success",
        payload=payload,
        headers=result.get("headers"),
        endpoint=result.get("endpoint"),
        response=full_response,
        http_status=result.get("status_code"),
        error_message=result.get("api_message") if result.get("is_duplicate") else None,
    )
    return True


def _apply_success(doc, doctype, fiscal_body, full_response=None, api_message=None, is_duplicate=False):
    fields_map = TotalVfdResponseParser.parse_fiscal_fields(fiscal_body)
    verification_link = fields_map.get("totalvfd_verification_link") or ""
    qr_data = QrGenerator.generate_base64(verification_link)

    notice = api_message or ""
    if is_duplicate and not notice:
        notice = "Reference number already used; existing fiscal receipt applied."

    stored_response = full_response if full_response is not None else fiscal_body
    values = {
        "totalvfd_fiscal_status": "Success",
        "totalvfd_sent": 1,
        "totalvfd_rctvnum": fields_map.get("totalvfd_rctvnum", ""),
        "totalvfd_verification_link": verification_link,
        "totalvfd_local_time": fields_map.get("totalvfd_local_time", ""),
        "totalvfd_rctnum": fields_map.get("totalvfd_rctnum", ""),
        "totalvfd_gc": fields_map.get("totalvfd_gc", ""),
        "totalvfd_z_number": fields_map.get("totalvfd_z_number", ""),
        "totalvfd_response": json.dumps(stored_response, indent=2, default=str),
        "totalvfd_error_message": None,
        "totalvfd_api_message": notice or None,
        "totalvfd_retry_count": 0,
    }
    if notice:
        values["totalvfd_api_message"] = notice
    frappe.db.set_value(doctype, doc.name, values, update_modified=False)

    qr_url = None
    if verification_link and qr_data:
        qr_url = _attach_qr_file(doc, doctype, verification_link, qr_data)

    _notify_fiscal_success(doc, doctype, values, verification_link, qr_url)


def _attach_qr_file(doc, doctype, verification_link, qr_b64):
    try:
        import base64

        content = base64.b64decode(qr_b64)
        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": f"totalvfd-qr-{doc.name}.png",
                "attached_to_doctype": doctype,
                "attached_to_name": doc.name,
                "content": content,
                "is_private": 0,
            }
        )
        file_doc.save(ignore_permissions=True)
        frappe.db.set_value(
            doctype,
            doc.name,
            "totalvfd_qr_code",
            file_doc.file_url,
            update_modified=False,
        )
        return file_doc.file_url
    except Exception as exc:
        _logger.warning("Could not attach QR for %s: %s", doc.name, exc)
    return None


def _notify_fiscal_success(doc, doctype, values, verification_link, qr_url):
    payload = {
        "doctype": doctype,
        "name": doc.name,
        "rctvnum": values.get("totalvfd_rctvnum"),
        "verification_link": verification_link,
        "qr_url": frappe.utils.get_url(qr_url) if qr_url else None,
        "api_message": values.get("totalvfd_api_message"),
    }
    frappe.publish_realtime("total_vfd_fiscal_done", payload, user=frappe.session.user)


def _mark_failed(doc, doctype, error_message, payload=None, log_values=None):
    retry_count = int(doc.get("totalvfd_retry_count") or 0) + 1
    values = {
        "totalvfd_fiscal_status": "Failed",
        "totalvfd_error_message": error_message,
        "totalvfd_api_message": None,
        "totalvfd_retry_count": retry_count,
    }
    if payload:
        values["totalvfd_payload"] = json.dumps(payload, indent=2, default=str)
    frappe.db.set_value(doctype, doc.name, values, update_modified=False)

    queue_payload = payload
    if queue_payload is None:
        try:
            builder = PayloadBuilder(doc.company)
            if doctype == "Sales Invoice":
                queue_payload = builder.build_from_sales_invoice(doc)
            else:
                queue_payload = builder.build_from_pos_invoice(doc)
        except Exception:
            queue_payload = None

    if queue_payload:
        from total_vfd.total_vfd.doctype.total_vfd_queue.total_vfd_queue import enqueue

        enqueue(doctype, doc.name, doc.company, queue_payload, error_message)

    log_vals = log_values or {}
    _create_log(
        doc,
        doctype,
        name=(payload or {}).get("referenceNumber", doc.name),
        status="Failed",
        payload=payload or {},
        headers=log_vals.get("headers"),
        endpoint=log_vals.get("endpoint", ""),
        response=log_vals.get("response"),
        error_message=error_message,
        http_status=log_vals.get("http_status"),
    )


def _create_log(
    doc,
    doctype,
    name,
    status,
    payload,
    headers=None,
    endpoint="",
    response=None,
    error_message=None,
    http_status=None,
):
    frappe.get_doc(
        {
            "doctype": "Total VFD Fiscal Log",
            "reference": name,
            "document_type": doctype,
            "document_name": doc.name,
            "company": doc.company,
            "endpoint": endpoint,
            "request_headers": json.dumps(headers, indent=2, default=str) if headers else "",
            "request_payload": json.dumps(payload, indent=2, default=str) if payload else "",
            "response_payload": json.dumps(response, indent=2, default=str) if response else "",
            "status": status,
            "error_message": error_message,
            "http_status": http_status or 0,
        }
    ).insert(ignore_permissions=True)


@frappe.whitelist()
def retry_fiscalisation(doctype, name):
    doc = frappe.get_doc(doctype, name)
    if not doc.get("totalvfd_fiscalise"):
        frappe.throw(_("Enable Fiscalise with Total VFD on this document first."))
    ok = _send_payload(doc, doctype, json.loads(doc.totalvfd_payload or "{}"), from_queue=True)
    if not ok:
        frappe.throw(doc.get("totalvfd_error_message") or _("Fiscalisation failed."))
    return {"ok": True}


def process_queue():
    from total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license import is_license_active
    from total_vfd.total_vfd.doctype.total_vfd_queue.total_vfd_queue import process_pending_queue

    if not is_license_active():
        return
    process_pending_queue()
