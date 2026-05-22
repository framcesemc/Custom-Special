frappe.ui.form.on("ABK Portal Settings", {
	refresh(frm) {
		const enabled = cint(frm.doc.allow_guest_submit_info);
		frm.add_custom_button(__(enabled ? "Nonaktifkan Guest Submit" : "Aktifkan Guest Submit"), () => {
			frm.set_value("allow_guest_submit_info", enabled ? 0 : 1);
			frm.save();
		}).toggleClass(enabled ? "btn-danger" : "btn-primary", true);
	},
});
