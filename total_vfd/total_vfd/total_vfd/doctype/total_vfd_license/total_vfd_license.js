frappe.ui.form.on("Total VFD License", {
	refresh(frm) {
		frm.disable_save();
		render_license_actions(frm);
		update_stepper(frm);
	},
});

function render_license_actions(frm) {
	frm.clear_custom_buttons();

	frm.add_custom_button(__("Copy Message for Vendor"), () => {
		frappe.call({
			method: "total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license.get_vendor_message",
			callback(r) {
				frappe.utils.copy_to_clipboard(r.message);
				frappe.show_alert({ message: __("Copied to clipboard"), indicator: "green" });
			},
		});
	});

	frm.add_custom_button(__("Register Vendor Code"), () => {
		frappe.prompt(
			[
				{
					fieldname: "vendor_activation_code",
					fieldtype: "Small Text",
					label: __("Vendor Activation Code"),
					reqd: 1,
				},
			],
			(values) => {
				frappe.call({
					method: "total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license.register_vendor_code",
					args: values,
					callback() {
						frm.reload_doc();
						frappe.show_alert({ message: __("Vendor code saved"), indicator: "green" });
					},
				});
			},
			__("Register Vendor Activation Code")
		);
	});

	if (frm.doc.status === "active") {
		frm.add_custom_button(__("Renew License"), () => open_activate_dialog(frm, true));
		frm.add_custom_button(__("Configure Company API"), () => {
			frappe.call({
				method: "total_vfd.api.setup_hub.get_setup_status",
				callback(r) {
					const company = r.message.default_company;
					if (company) {
						frappe.set_route("Form", "Company", company);
					} else {
						frappe.set_route("List", "Company");
					}
				},
			});
		});
		if (frappe.user.has_role("System Manager") || frappe.user.has_role("Total VFD Manager")) {
			frm.add_custom_button(__("Revoke License"), () => {
				frappe.confirm(__("Revoke this module license? Fiscalisation will stop."), () => {
					frappe.call({
						method: "total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license.revoke_license",
						callback() {
							frm.reload_doc();
						},
					});
				});
			});
		}
	} else {
		frm.add_custom_button(__("Activate License"), () => open_activate_dialog(frm, false), __("Actions"));
	}

	frm.add_custom_button(__("Open Setup Hub"), () => frappe.set_route("Form", "Total VFD Settings", "Total VFD Settings"));
}

function open_activate_dialog(frm, renew) {
	const fields = [
		{
			fieldname: "license_word",
			fieldtype: "Data",
			label: __("Your License Word"),
			read_only: 1,
			default: frm.doc.license_word,
		},
		{
			fieldname: "activation_phrase",
			fieldtype: "Data",
			label: __("Activation Phrase (automatic)"),
			read_only: 1,
			default: frm.doc.activation_phrase,
		},
	];
	if (!renew) {
		fields.push({
			fieldname: "vendor_activation_code",
			fieldtype: "Small Text",
			label: __("Vendor Activation Code"),
			default: frm.doc.pending_vendor_activation_code || "",
		});
	}
	fields.push({
		fieldname: "license_key",
		fieldtype: "Data",
		label: __("License Key"),
		reqd: 1,
	});

	frappe.prompt(
		fields,
		(values) => {
			frappe.call({
				method: "total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license.activate_license",
				args: {
					license_key: values.license_key,
					vendor_activation_code: values.vendor_activation_code,
					renew: renew ? 1 : 0,
				},
				callback(r) {
					frm.reload_doc();
					const msg = __("License {0} until {1} ({2} days remaining).", [
						renew ? __("renewed") : __("activated"),
						r.message.expiry_date,
						r.message.days_until_expiry,
					]);
					frappe.msgprint({
						title: __("License Active"),
						message: msg,
						primary_action: {
							label: __("Configure Company API"),
							action() {
								const company = r.message.default_company;
								if (company) {
									frappe.set_route("Form", "Company", company);
								} else {
									frappe.set_route("List", "Company");
								}
							},
						},
					});
				},
			});
		},
		renew ? __("Renew Total VFD License") : __("Activate Total VFD License")
	);
}

function update_stepper(frm) {
	const steps = [
		{ label: __("Word assigned"), done: !!frm.doc.license_word },
		{
			label: __("Vendor code saved"),
			done: !!(frm.doc.pending_vendor_activation_code || frm.doc.status === "active"),
		},
		{ label: __("License active"), done: frm.doc.status === "active" },
	];
	const html = steps
		.map(
			(s, i) =>
				`<span class="badge ${s.done ? "badge-success" : "badge-secondary"}">${i + 1}. ${s.label}</span>`
		)
		.join(" &nbsp; ");
	frm.dashboard.set_headline_alert(html, frm.doc.status !== "active" ? "orange" : "green");
}
