from frappe.model.document import Document

from custom_special.abk_portal.media import validate_media_row


class ABKPlaceMedia(Document):
	def validate(self):
		validate_media_row(self)
