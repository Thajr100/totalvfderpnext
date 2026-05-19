frappe.ui.form.on("Company", {
	refresh(frm) {
		if (!frm.fields_dict.totalvfd_tab) return;
		total_vfd.show_license_banner(frm, null, frm.doc.name);
		if (frm.doc.name) {
			frm.set_df_property(
				"totalvfd_bearer_token",
				"description",
				__(
					"From your Total VFD portal. You need an active license in Total VFD Settings for this company first."
				)
			);
			render_company_license_actions(frm);
		}
	},
});

function render_company_license_actions(frm) {
	if (!frm.fields_dict.totalvfd_license_status) return;

	frappe.call({
		method: "total_vfd.api.setup_hub.get_setup_status",
		args: { company: frm.doc.name },
		callback(r) {
			const s = r.message;
			if (frm.doc.totalvfd_license_site_id !== s.site_id) {
				frm.set_value("totalvfd_license_site_id", s.site_id);
			}
			if (frm.doc.totalvfd_license_word !== (s.license_word || "")) {
				frm.set_value("totalvfd_license_word", s.license_word || "");
			}
			if (frm.doc.totalvfd_license_status !== (s.license_status || "")) {
				frm.set_value("totalvfd_license_status", s.license_status || "");
			}

			frm.clear_custom_button(__("License"));
			if (frappe.user.has_role("System Manager") || frappe.user.has_role("Total VFD Manager")) {
				frm.add_custom_button(__("Open setup checklist"), () => {
					frappe.set_route("Form", "Total VFD Settings", "Total VFD Settings");
				}, __("License"));

				if (s.validation_configured && s.license_word) {
					frm.add_custom_button(__("Copy email for vendor"), () => {
						frappe.call({
							method:
								"total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license.get_vendor_message",
							args: { company: frm.doc.name },
							callback(res) {
								frappe.utils.copy_to_clipboard(res.message);
								frappe.show_alert({ message: __("Copied"), indicator: "green" });
							},
						});
					}, __("License"));
				}

				if (s.validation_configured && !s.license_active) {
					frm.add_custom_button(__("Activate license"), () => {
						frappe.set_route("Form", "Total VFD Settings", "Total VFD Settings");
					}, __("License"));
				}
			}
		},
	});
}
