from frappe.model.document import Document

from custom_special.abk_portal.utils import make_unique_slug


class ShadowTeacher(Document):
	def before_insert(self):
		self.set_slug()

	def before_validate(self):
		self.set_slug()

	def set_slug(self):
		if not self.slug:
			self.slug = make_unique_slug("Shadow Teacher", f"{self.teacher_name} {self.city}", self.name)
