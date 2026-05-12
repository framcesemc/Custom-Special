from frappe.model.document import Document

from custom_special.abk_portal.notifications import notify_system_managers


class ParentInquiry(Document):
	def after_insert(self):
		notify_system_managers(
			"Permintaan info baru",
			"Ada parent yang meminta bantuan/info admin.",
			self.doctype,
			self.name,
		)
