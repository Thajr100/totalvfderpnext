frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.totalvfd_fiscal_status === "Success") {
			frm.add_custom_button(__("Print (Total VFD)"), () => {
				frappe.ui.form.print(frm.doc.doctype, frm.doc.name, "Sales Invoice - Total VFD");
			});
		}
		if (frm.doc.docstatus === 1 && frm.doc.totalvfd_fiscalise) {
			frm.add_custom_button(__("Fiscal Logs"), () => total_vfd.open_fiscal_logs(frm));
		}
		if (frm.doc.docstatus !== 1 || !frm.doc.totalvfd_fiscalise) return;
		if (frm.doc.totalvfd_fiscal_status === "Success") return;
		frm.add_custom_button(__("Retry Total VFD"), () => {
			frappe.call({
				method: "total_vfd.api.fiscal_service.retry_fiscalisation",
				args: { doctype: frm.doctype, name: frm.doc.name },
				freeze: true,
				callback() {
					frm.reload_doc();
				},
			});
		});
	},
});
