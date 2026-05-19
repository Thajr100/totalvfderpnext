frappe.ready(() => {
	if (!frappe.boot.total_vfd_show_welcome || frappe.boot.total_vfd_setup_complete) {
		return;
	}
	if (!(frappe.user.has_role("System Manager") || frappe.user.has_role("Total VFD Manager"))) {
		return;
	}
	if (sessionStorage.getItem("total_vfd_welcome_shown")) {
		return;
	}
	sessionStorage.setItem("total_vfd_welcome_shown", "1");

	frappe.msgprint({
		title: __("Welcome to Total VFD"),
		message: __(
			"Open the setup checklist. If you do not have the license server address and password, " +
				"use Copy note for IT and send it to your support team."
		),
		indicator: "blue",
		primary_action: {
			label: __("Open setup checklist"),
			action() {
				frappe.set_route("Form", "Total VFD Settings", "Total VFD Settings");
			},
		},
		secondary_action: {
			label: __("Later"),
			action() {
				frappe.call({ method: "total_vfd.api.setup_hub.dismiss_setup_welcome" });
			},
		},
	});
});
