frappe.realtime.on("total_vfd_fiscal_done", (data) => {
	if (!data || !data.rctvnum) return;

	let message = __("Fiscal receipt: {0}", [data.rctvnum]);
	if (data.api_message) {
		message += `<br><small>${frappe.utils.escape_html(data.api_message)}</small>`;
	}

	const dialog = new frappe.ui.Dialog({
		title: __("Total VFD — Fiscalised"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "fiscal_html",
				options: `<p>${message}</p>`,
			},
		],
		primary_action_label: __("OK"),
		primary_action() {
			dialog.hide();
		},
	});

	if (data.qr_url) {
		const qrUrl = frappe.utils.escape_html(data.qr_url);
		dialog.fields_dict.fiscal_html.$wrapper.append(
			`<div style="text-align:center;margin-top:12px;">
				<img src="${qrUrl}" alt="QR" style="max-width:180px;max-height:180px;" />
			</div>`
		);
	}
	if (data.verification_link) {
		const verificationLink = frappe.utils.escape_html(data.verification_link);
		dialog.fields_dict.fiscal_html.$wrapper.append(
			`<p style="font-size:11px;word-break:break-all;margin-top:8px;">
				<a href="${verificationLink}" target="_blank" rel="noopener noreferrer">${verificationLink}</a>
			</p>`
		);
	}

	dialog.show();
	frappe.show_alert({ message: __("Fiscalised: {0}", [data.rctvnum]), indicator: "green" });
});
