frappe.ui.form.on("ABK Place Experience", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		if (frappe.user.has_role("System Manager") || frappe.user.has_role("ABK Admin")) {
			if (frm.doc.verification_status !== "Approved") {
				frm.add_custom_button(__("Approve"), () => {
					frappe.call({
						method: "custom_special.abk_portal.doctype.abk_place_experience.abk_place_experience.approve_experience",
						args: { name: frm.doc.name },
						callback: () => frm.reload_doc(),
					});
				}, __("Moderation"));
			}

			if (frm.doc.verification_status !== "Rejected") {
				frm.add_custom_button(__("Reject"), () => {
					frappe.call({
						method: "custom_special.abk_portal.doctype.abk_place_experience.abk_place_experience.reject_experience",
						args: { name: frm.doc.name },
						callback: () => frm.reload_doc(),
					});
				}, __("Moderation"));
			}
		}
	},
});
