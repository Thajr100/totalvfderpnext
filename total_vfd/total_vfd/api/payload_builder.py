import json
import logging
import re

import frappe
from frappe.utils import flt

_logger = logging.getLogger(__name__)

TIN_PATTERN = re.compile(r"^\d{9}$")
ID_TYPE_TIN = 1
ID_TYPE_NONE = 6
VAT_RATE_STANDARD = 18.0
VAT_GROUP_STANDARD = "A"
VAT_GROUP_ZERO = "C"
RATE_TOLERANCE = 0.001


class PayloadBuilder:
    def __init__(self, company_name):
        self.company_name = company_name
        self.company = frappe.get_doc("Company", company_name)

    def build_from_sales_invoice(self, doc):
        if doc.docstatus != 1:
            raise ValueError("Sales Invoice must be submitted before fiscalisation.")
        if doc.is_return:
            raise ValueError("Credit notes are not fiscalised.")
        items = self._build_sales_invoice_items(doc)
        return {
            "referenceNumber": doc.name,
            "serial": self.company.totalvfd_serial,
            "items": items,
            "customer": self._build_customer(doc.customer),
            "payments": self._build_payments_from_items(
                items,
                doc.grand_total,
                payment_type="invoice",
            ),
        }

    def build_from_pos_invoice(self, doc):
        if doc.docstatus != 1:
            raise ValueError("POS Invoice must be submitted before fiscalisation.")
        items = self._build_pos_items(doc)
        items = self._reconcile_items_to_document_total(items, doc.grand_total)
        ref = doc.pos_invoice or doc.name
        return {
            "referenceNumber": ref,
            "serial": self.company.totalvfd_serial,
            "items": items,
            "customer": self._build_customer(doc.customer),
            "payments": self._build_pos_payments(doc, items),
        }

    def _build_sales_invoice_items(self, doc):
        items = []
        for row in doc.items:
            if not row.item_code or row.qty == 0:
                continue
            item = self._build_item_from_si_row(row, doc)
            if item["price"] or item["qty"]:
                items.append(item)
        if not items:
            raise ValueError("No fiscalisable lines found on the document.")
        return items

    def _build_pos_items(self, doc):
        items = []
        for row in doc.items:
            if row.qty == 0:
                continue
            items.append(self._build_item_from_pos_row(row, doc))
        if not items:
            raise ValueError("No fiscalisable lines found on the POS invoice.")
        return items

    def _build_item_from_si_row(self, row, doc):
        discount = self._si_discount_amount(row)
        net_tax_incl = self._si_line_total_tax_inclusive(row, doc)
        line_price = round(net_tax_incl + discount, 2)
        product = frappe.get_cached_doc("Item", row.item_code) if row.item_code else None
        return {
            "id": self._product_reference(product, row.item_code),
            "name": row.item_name or row.description or row.item_code,
            "price": line_price,
            "qty": abs(flt(row.qty)),
            "vatGroup": self._get_vat_group(product, row, doc),
            "discount": round(discount, 2),
        }

    def _build_item_from_pos_row(self, row, doc):
        discount = self._pos_discount_amount(row)
        net_tax_incl = self._pos_line_total_tax_inclusive(row, doc)
        line_price = round(net_tax_incl + discount, 2)
        product = frappe.get_cached_doc("Item", row.item_code) if row.item_code else None
        return {
            "id": self._product_reference(product, row.item_code),
            "name": row.item_name or row.item_code,
            "price": line_price,
            "qty": abs(flt(row.qty)),
            "vatGroup": self._get_vat_group(product, row, doc),
            "discount": round(discount, 2),
        }

    @staticmethod
    def _si_discount_amount(row):
        if flt(row.discount_amount):
            return abs(flt(row.discount_amount))
        if flt(row.discount_percentage):
            return abs(flt(row.rate) * flt(row.qty) * flt(row.discount_percentage) / 100.0)
        return 0.0

    @staticmethod
    def _pos_discount_amount(row):
        if flt(row.discount_percentage):
            return abs(flt(row.rate) * flt(row.qty) * flt(row.discount_percentage) / 100.0)
        return 0.0

    def _si_line_total_tax_inclusive(self, row, doc):
        tax_amount = flt(getattr(row, "tax_amount", 0) or 0)
        if tax_amount:
            return abs(flt(row.amount) + tax_amount)
        rate = self._row_tax_rate(row, doc)
        if rate:
            return abs(flt(row.amount) * (1 + rate / 100.0))
        return abs(flt(row.amount))

    def _pos_line_total_tax_inclusive(self, row, doc):
        if flt(row.tax_amount):
            return abs(flt(row.amount) + flt(row.tax_amount))
        rate = self._row_tax_rate(row, doc)
        if rate:
            return abs(flt(row.amount) * (1 + rate / 100.0))
        return abs(flt(row.amount))

    def _row_tax_rate(self, row, doc):
        rates = self._row_tax_rates(row, doc)
        return max(rates) if rates else 0.0

    def _row_tax_rates(self, row, doc):
        rates = []
        if flt(row.tax_rate):
            rates.append(flt(row.tax_rate))
        item_tax_rate = getattr(row, "item_tax_rate", None) or row.get("item_tax_rate")
        if item_tax_rate:
            try:
                parsed = json.loads(item_tax_rate) if isinstance(item_tax_rate, str) else item_tax_rate
            except (TypeError, ValueError):
                parsed = {}
            if isinstance(parsed, dict):
                rates.extend(flt(rate) for rate in parsed.values())
        for tax in doc.get("taxes") or []:
            if tax.charge_type == "On Net Total" and flt(tax.rate):
                rates.append(flt(tax.rate))
        return rates

    def _product_reference(self, product, item_code):
        if product and product.get("item_code"):
            return product.item_code
        return item_code or "0"

    def _get_vat_group(self, product, row, doc):
        default = self.company.get("totalvfd_default_vat_group") or "A"
        mode = self.company.get("totalvfd_vat_mapping_mode") or "auto"
        if mode == "manual":
            return self._get_vat_group_manual(product, row, default)
        if self.company.get("totalvfd_use_default_vat_group_all"):
            return default
        for rate in sorted(self._row_tax_rates(row, doc), reverse=True):
            if abs(rate - VAT_RATE_STANDARD) < RATE_TOLERANCE:
                return VAT_GROUP_STANDARD
            if abs(rate) < RATE_TOLERANCE:
                return VAT_GROUP_ZERO
        return default

    def _get_vat_group_manual(self, product, row, default):
        template_name = getattr(row, "item_tax_template", None) or row.get("item_tax_template")
        if template_name:
            tax_group = frappe.db.get_value("Item Tax Template", template_name, "totalvfd_vat_group")
            if tax_group:
                return tax_group
        if product and product.get("totalvfd_vat_group"):
            return product.totalvfd_vat_group
        return default

    def _build_customer(self, customer_name):
        if not customer_name:
            return {
                "name": "Walk-in Customer",
                "mobile": "",
                "idType": ID_TYPE_NONE,
                "idValue": "",
            }
        partner = frappe.get_doc("Customer", customer_name)
        mobile = self._normalize_mobile(partner)
        id_type, id_value = self._resolve_tin(partner)
        return {
            "name": partner.customer_name or customer_name,
            "mobile": mobile,
            "idType": id_type,
            "idValue": id_value,
        }

    def _normalize_mobile(self, partner):
        for field_name in ("mobile_no", "phone", "mobile"):
            value = partner.get(field_name)
            if value:
                return re.sub(r"\s+", "", value)
        return ""

    def _resolve_tin(self, partner):
        tin = (partner.get("tax_id") or partner.get("pan") or "").strip()
        tin_digits = re.sub(r"\D", "", tin)
        if tin_digits and TIN_PATTERN.match(tin_digits):
            return ID_TYPE_TIN, tin_digits
        if tin_digits and not TIN_PATTERN.match(tin_digits):
            _logger.warning("Invalid TIN for customer %s: %s", partner.name, tin)
        return ID_TYPE_NONE, ""

    @staticmethod
    def _format_payment_type(payment_type):
        text = (payment_type or "invoice").strip()
        if not text:
            return "invoice"
        return text[0].lower() + text[1:]

    @staticmethod
    def _payment_amount_from_items(items):
        if not items:
            return 0.0
        return round(sum(item["price"] - item["discount"] for item in items), 2)

    def _build_payments_from_items(self, items, document_total, payment_type="invoice"):
        amount = self._payment_amount_from_items(items)
        if not amount and document_total:
            amount = round(abs(flt(document_total)), 2)
        return [{"type": self._format_payment_type(payment_type), "amount": amount}]

    def _reconcile_items_to_document_total(self, items, document_total):
        if not items:
            return items
        items_total = self._payment_amount_from_items(items)
        doc_total = round(abs(flt(document_total)), 2)
        diff = round(doc_total - items_total, 2)
        if abs(diff) >= 0.01:
            items[-1]["price"] = round(items[-1]["price"] + diff, 2)
        return items

    def _build_pos_payments(self, doc, items):
        amount = self._payment_amount_from_items(items)
        if not amount and doc.grand_total:
            amount = round(abs(flt(doc.grand_total)), 2)
        payment_type = "cash"
        payments = doc.get("payments") or []
        if payments:
            first_payment = payments[0]
            payment_type = (
                first_payment.get("mode_of_payment")
                or first_payment.get("payment_method")
                or payment_type
            )
        return [{"type": self._format_payment_type(payment_type), "amount": amount}]
