frappe.ui.form.on("Total VFD License", {
	onload(frm) {
		frappe.show_alert({
			message: __("License setup has moved to Total VFD Settings."),
			indicator: "blue",
		});
		frappe.set_route("Form", "Total VFD Settings", "Total VFD Settings");
	},
});
