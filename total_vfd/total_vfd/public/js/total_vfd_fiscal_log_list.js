frappe.listview_settings["Total VFD Fiscal Log"] = {
	onload(listview) {
		const opts = frappe.route_options || {};
		if (opts.document_type) {
			listview.filter_area.add([
				["Total VFD Fiscal Log", "document_type", "=", opts.document_type],
			]);
		}
		if (opts.document_name) {
			listview.filter_area.add([
				["Total VFD Fiscal Log", "document_name", "=", opts.document_name],
			]);
		}
	},
};
