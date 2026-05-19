frappe.ui.form.on("Total VFD Settings", {
	onload(frm) {
		frm.set_intro(
			__(
				"Follow the checklist below. Step 1 is usually done by IT using details from your software vendor."
			),
			"blue"
		);
		ensure_site_id(frm);
	},
	refresh(frm) {
		render_guided_setup(frm);
		if (frappe.user.has_role("System Manager") || frappe.user.has_role("Total VFD Manager")) {
			frm.add_custom_button(__("Test link to vendor"), () => test_connection(frm));
			frm.add_custom_button(__("Is my license OK?"), () => check_license(frm));
			frm.add_custom_button(__("Get my license word"), () => refresh_word(frm));
			frm.add_custom_button(__("Copy note for IT"), () => copy_it_note(frm));
		}
	},
});

function ensure_site_id(frm) {
	frappe.call({
		method: "total_vfd.api.license_store.get_site_id_api",
		args: { company: frm._total_vfd_company },
		callback(r) {
			if (r.message) frm.set_value("site_id", r.message);
		},
	});
}

function test_connection(frm) {
	frappe.call({
		method: "total_vfd.total_vfd.doctype.total_vfd_settings.total_vfd_settings.test_validation_connection",
		freeze: true,
		callback(r) {
			frappe.msgprint(r.message.message || __("Link to vendor works."), __("Success"));
		},
	});
}

function check_license(frm) {
	frappe.call({
		method: "total_vfd.total_vfd.doctype.total_vfd_settings.total_vfd_settings.check_license_now",
		args: { company: frm._total_vfd_company },
		freeze: true,
		callback(r) {
			const m = r.message;
			let msg = __("Your license is: {0}", [m.status]);
			if (m.expiry_date) msg += "<br>" + __("Valid until: {0}", [m.expiry_date]);
			if (m.warning) msg += "<br><b>" + frappe.utils.escape_html(m.warning) + "</b>";
			frappe.msgprint(msg, __("License"));
			render_guided_setup(frm);
		},
	});
}

function copy_it_note(frm) {
	frappe.call({
		method: "total_vfd.api.setup_hub.get_it_request_message",
		callback(r) {
			frappe.utils.copy_to_clipboard(r.message);
			frappe.show_alert({ message: __("Copied — send to IT or support"), indicator: "green" });
		},
	});
}

function refresh_word(frm) {
	frappe.call({
		method: "total_vfd.total_vfd.doctype.total_vfd_settings.total_vfd_settings.refresh_license_word",
		args: { company: frm._total_vfd_company },
		freeze: true,
		callback(r) {
			const m = r.message;
			frappe.show_alert({
				message: m.base_word
					? __("Your code word is: {0}", [m.base_word])
					: __("Updated from vendor"),
				indicator: "green",
			});
			render_guided_setup(frm);
		},
	});
}

function render_company_picker(frm, $wrapper, status) {
	$wrapper.find(".total-vfd-company-picker").remove();
	const companies = frappe.boot.user.companies || [];
	if (!companies.length) return;

	const current = frm._total_vfd_company || status.company;
	const $pick = $("<div>").addClass("total-vfd-company-picker").css("margin-bottom", "16px");
	$pick.append($("<label>").addClass("control-label").text(__("Which company?")));
	const $sel = $("<select>").addClass("form-control").css("max-width", "320px");
	$pick.append($sel);
	$wrapper.prepend($pick);

	companies.forEach((c) => {
		$sel.append($("<option>").attr("value", c).text(c));
	});
	if (current) $sel.val(current);
	$sel.on("change", () => {
		frm._total_vfd_company = $sel.val();
		ensure_site_id(frm);
		render_guided_setup(frm);
	});
}

function render_guided_setup(frm) {
	const $wrapper = frm.fields_dict.help_html.$wrapper;
	$wrapper.find(".total-vfd-wizard").remove();

	frappe.call({
		method: "total_vfd.api.setup_hub.get_guided_steps",
		args: { company: frm._total_vfd_company },
		callback(r) {
			const data = r.message;
			const status = data.status;
			frm._total_vfd_company = status.company;

			if (status.multi_company) {
				render_company_picker(frm, $wrapper, status);
			}

			if (!status.validation_configured) {
				frm.dashboard.set_headline_alert(
					__("Complete Step 1 above (address + password), Save, then Test link to vendor."),
					"orange"
				);
			} else if (status.license_warning) {
				frm.dashboard.set_headline_alert(status.license_warning, "red");
			} else if (data.all_ready) {
				frm.dashboard.set_headline_alert(__("Ready — you can fiscalise invoices."), "green");
			} else {
				frm.dashboard.set_headline_alert(__("Complete the steps below."), "blue");
			}

			const pct = data.progress_percent;
			const $wiz = $("<div>").addClass("total-vfd-wizard").css("max-width", "720px");
			$wiz.append($("<h4>").css("margin-bottom", "8px").text(__("Setup progress")));
			const $prog = $("<div>").addClass("progress").css({ height: "22px", "margin-bottom": "20px" });
			$prog.append(
				$("<div>")
					.addClass("progress-bar progress-bar-success")
					.css("width", pct + "%")
					.text(pct + "%")
			);
			$wiz.append($prog);
			$wrapper.append($wiz);

			const $list = $("<div>").addClass("total-vfd-steps");
			$wiz.append($list);

			data.steps.forEach((step) => {
				const done = step.done;
				const optional = step.optional;
				const icon = done ? "\u2713" : String(step.number);
				const border = done ? "#28a745" : "#ddd";
				const $card = $("<div>")
					.addClass("panel panel-default")
					.css({
						"margin-bottom": "12px",
						padding: "14px",
						"border-radius": "8px",
						border: "2px solid " + border,
					});
				const $row = $("<div>").css({ display: "flex", gap: "12px" });
				$row.append(
					$("<div>").css({ "font-size": "20px", "font-weight": "bold", "min-width": "28px" }).text(icon)
				);
				const $body = $("<div>").css("flex", "1");
				$body.append(
					$("<div>")
						.css("font-weight", "600")
						.text(step.title + (optional ? " (" + __("optional") + ")" : ""))
				);
				$body.append($("<p>").addClass("text-muted").css("margin", "8px 0").text(step.help));
				const $actions = $("<div>").addClass("step-actions");
				$body.append($actions);
				$row.append($body);
				$card.append($row);
				$list.append($card);

				if (step.id === "vendor_message" && status.license_word) {
					$actions.append(
						$("<p>").text(__("Your code word for this company: {0}", [status.license_word]))
					);
				}

				if (step.action === "validation" && !step.done) {
					const $it = $("<button>").addClass("btn btn-default btn-sm").text(__("Copy note for IT"));
					$actions.append($it);
					$it.on("click", () => copy_it_note(frm));
				}

				if (step.action === "copy_vendor" && status.validation_configured) {
					const $btn = $("<button>")
						.addClass("btn btn-primary btn-sm")
						.text(__("Copy email for vendor"));
					$actions.append($btn);
					$btn.on("click", () => {
						frappe.call({
							method:
								"total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license.get_vendor_message",
							args: { company: frm._total_vfd_company },
							callback(res) {
								frappe.utils.copy_to_clipboard(res.message);
								frappe.show_alert({
									message: __("Copied to clipboard"),
									indicator: "green",
								});
							},
						});
					});
				}

				if (step.action === "activate" && !done && status.validation_configured) {
					const $btn = $("<button>")
						.addClass("btn btn-primary btn-sm")
						.text(__("Enter vendor code and key"));
					$actions.append($btn);
					$btn.on("click", () =>
						total_vfd_open_activate_dialog(
							status.license_word,
							status.activation_phrase,
							frm._total_vfd_company
						)
					);
				}

				if (step.action === "open_company" && status.default_company) {
					const $btn = $("<button>").addClass("btn btn-primary btn-sm").text(__("Open Company settings"));
					$actions.append($btn);
					$btn.on("click", () => frappe.set_route("Form", "Company", status.default_company));
				}

				if (step.action === "open_pos_profile") {
					const $btn = $("<button>").addClass("btn btn-default btn-sm").text(__("POS profiles"));
					$actions.append($btn);
					$btn.on("click", () => frappe.set_route("List", "POS Profile"));
				}

				if (step.action === "open_sales_invoice") {
					const $btn = $("<button>").addClass("btn btn-default btn-sm").text(__("New Sales Invoice"));
					$actions.append($btn);
					$btn.on("click", () => frappe.new_doc("Sales Invoice"));
				}
			});


			if (data.all_ready && !status.setup_complete) {
				const $finish = $("<button>")
					.addClass("btn btn-success btn-finish")
					.css("margin-top", "12px")
					.text(__("I finished setup"));
				$wiz.append($finish);
				$finish.on("click", () => {
					frappe.call({
						method: "total_vfd.api.setup_hub.mark_setup_complete",
						callback() {
							frappe.call({ method: "total_vfd.api.setup_hub.dismiss_setup_welcome" });
							frm.reload_doc();
						},
					});
				});
			}
		},
	});
}

function total_vfd_open_activate_dialog(license_word, activation_phrase, company) {
	const phrase = activation_phrase || (license_word ? license_word + "Tanzania" : "");
	frappe.prompt(
		[
			{
				fieldname: "vendor_activation_code",
				fieldtype: "Small Text",
				label: __("Short code from vendor email"),
				reqd: 1,
			},
			{
				fieldname: "license_key",
				fieldtype: "Data",
				label: __("License key from vendor email"),
				reqd: 1,
			},
		],
		(values) => {
			frappe.call({
				method: "total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license.activate_license",
				args: {
					license_key: values.license_key,
					vendor_activation_code: values.vendor_activation_code,
					renew: 0,
					company: company,
				},
				callback(res) {
					frappe.show_alert({
						message: __("License works until {0}", [res.message.expiry_date]),
						indicator: "green",
					});
					frappe.ui.form.get_open_form("Total VFD Settings")?.refresh();
				},
			});
		},
		__("Turn on license"),
		__("Activate")
	);
}
