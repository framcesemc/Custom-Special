import frappe

def get_context(context):
	context.no_cache = 1
	context.title = "Bagikan Info Tempat"
	
	if frappe.session.user == "Guest":
		context.is_guest = True
	else:
		context.is_guest = False
		
	context.place_types = ["School", "Therapy Center", "ABK Friendly Place"]
	context.parents = [{"name": "ABK Portal", "route": "/abk"}]
