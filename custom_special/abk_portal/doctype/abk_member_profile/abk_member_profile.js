frappe.ui.form.on("ABK Member Profile", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		const can_review = frappe.user.has_role("ABK Admin") || frappe.user.has_role("System Manager");
		if (!can_review) {
			return;
		}

		if (frm.doc.verification_status !== "Verified") {
			frm.add_custom_button(__("Verify Member"), () => {
				frappe.call({
					method: "custom_special.abk_portal.doctype.abk_member_profile.abk_member_profile.verify_member",
					args: { name: frm.doc.name },
					callback() {
						frm.reload_doc();
					},
				});
			});
		}

		if (frm.doc.verification_status !== "Rejected") {
			frm.add_custom_button(__("Reject Member"), () => {
				frappe.confirm(__("Reject this ABK member?"), () => {
					frappe.call({
						method: "custom_special.abk_portal.doctype.abk_member_profile.abk_member_profile.reject_member",
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
