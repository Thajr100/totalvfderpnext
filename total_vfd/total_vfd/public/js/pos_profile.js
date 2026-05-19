frappe.ui.form.on("POS Profile", {
	refresh(frm) {
		if (frm.doc.totalvfd_use_fiscal_print_format && !frm.doc.print_format) {
			frm.set_value("print_format", "POS Invoice - Total VFD");
		}
	},
	totalvfd_use_fiscal_print_format(frm) {
		if (frm.doc.totalvfd_use_fiscal_print_format) {
			frm.set_value("print_format", "POS Invoice - Total VFD");
		}
	},
});
