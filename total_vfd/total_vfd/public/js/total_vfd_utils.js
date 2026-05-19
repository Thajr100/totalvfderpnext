frappe.provide("total_vfd");

total_vfd.open_fiscal_logs = function (frm) {
	frappe.route_options = {
		document_type: frm.doctype,
		document_name: frm.doc.name,
	};
	frappe.set_route("List", "Total VFD Fiscal Log");
};

total_vfd.open_company_api_settings = function (company) {
	const route = company
		? `/app/company/${company}`
		: "/app/company";
	frappe.set_route(route.replace("/app/", "").split("/").join("/"));
	if (company) {
		frappe.set_route("Form", "Company", company);
	} else {
		frappe.set_route("List", "Company");
	}
};

total_vfd.show_license_banner = function (frm, callback, company) {
	frappe.call({
		method: "total_vfd.api.setup_hub.get_license_banner",
		args: { company: company || (frm.doc && frm.doc.company) || frm.doc.name },
		callback(r) {
			if (r.message && r.message.message) {
				const color = r.message.level === "warning" ? "orange" : "orange";
				frm.dashboard.set_headline_alert(r.message.message, color);
			}
			if (callback) callback(r.message);
		},
	});
};

total_vfd.render_setup_checklist = function (container, status) {
	const steps = [
		{ label: __("License word assigned"), done: status.word_assigned },
		{ label: __("Vendor code saved"), done: status.vendor_code_saved },
		{ label: __("License active"), done: status.license_active },
		{ label: __("API configured on Company"), done: status.api_configured },
	];
	const html = `
		<div class="total-vfd-setup-checklist" style="margin-bottom: 12px;">
			${steps
				.map(
					(s, i) =>
						`<span class="badge ${s.done ? "badge-success" : "badge-secondary"}">${i + 1}. ${s.label}</span>`
				)
				.join(" &nbsp; ")}
		</div>`;
	container.html(html);
};
