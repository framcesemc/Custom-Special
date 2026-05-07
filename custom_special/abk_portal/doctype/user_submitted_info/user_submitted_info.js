frappe.ui.form.on("User Submitted Info", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		const can_review = frappe.user.has_role("ABK Admin") || frappe.user.has_role("System Manager");
		if (!can_review) {
			return;
		}

		if (frm.doc.verification_status !== "Approved" && !frm.doc.approved_place) {
			frm.add_custom_button(__("Approve and Create ABK Place"), () => {
				frappe.call({
					method: "custom_special.abk_portal.doctype.user_submitted_info.user_submitted_info.approve_and_create_abk_place",
					args: { name: frm.doc.name },
					callback() {
						frm.reload_doc();
					},
				});
			});
		}

		if (frm.doc.verification_status !== "Rejected") {
			frm.add_custom_button(__("Reject"), () => {
				frappe.confirm(__("Reject this submitted info?"), () => {
					frappe.call({
						method: "custom_special.abk_portal.doctype.user_submitted_info.user_submitted_info.reject_submission",
						args: { name: frm.doc.name },
						callback() {
							frm.reload_doc();
						},
					});
				});
			});
		}
	},
});
