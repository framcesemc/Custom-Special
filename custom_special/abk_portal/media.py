from pathlib import PurePosixPath
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _
from frappe.utils import cstr


ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov"}
ALLOWED_MEDIA_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}
MEDIA_VALIDATION_MESSAGE = _(
	"File tidak diizinkan. Hanya foto JPG, PNG, WEBP dan video MP4, WEBM, MOV yang diperbolehkan."
)


def get_media_extension(value):
	value = cstr(value).strip()
	if not value:
		return ""

	path = urlparse(value).path if "://" in value else value
	suffix = PurePosixPath(path).suffix.lower().lstrip(".")
	return suffix


def get_media_kind(value):
	if get_youtube_embed_url(value):
		return "YouTube"

	extension = get_media_extension(value)
	if extension in ALLOWED_IMAGE_EXTENSIONS:
		return "Image"
	if extension in ALLOWED_VIDEO_EXTENSIONS:
		return "Video"
	return "URL"


def get_youtube_embed_url(value):
	parsed = urlparse(cstr(value).strip())
	host = parsed.netloc.lower()
	if host not in YOUTUBE_HOSTS:
		return ""

	video_id = ""
	if host in {"youtu.be", "www.youtu.be"}:
		video_id = parsed.path.strip("/").split("/")[0]
	elif parsed.path == "/watch":
		video_id = parse_qs(parsed.query).get("v", [""])[0]
	elif parsed.path.startswith("/embed/"):
		video_id = parsed.path.split("/embed/", 1)[1].split("/")[0]
	elif parsed.path.startswith("/shorts/"):
		video_id = parsed.path.split("/shorts/", 1)[1].split("/")[0]

	if not video_id:
		return ""

	return f"https://www.youtube.com/embed/{video_id}"


def validate_media_value(value, media_type=None, allow_external_url=True):
	value = cstr(value).strip()
	if not value:
		return

	if get_youtube_embed_url(value):
		return

	extension = get_media_extension(value)
	if extension in ALLOWED_MEDIA_EXTENSIONS:
		return

	if allow_external_url and media_type == "URL" and "://" in value and not extension:
		return

	frappe.throw(MEDIA_VALIDATION_MESSAGE)


def validate_media_row(row):
	media_type = cstr(row.get("media_type")).strip()
	for fieldname in ("media_file", "media_url"):
		value = cstr(row.get(fieldname)).strip()
		if value:
			validate_media_value(value, media_type=media_type, allow_external_url=(fieldname == "media_url"))


def normalize_public_media(row):
	source = cstr(row.get("media_file") or row.get("media_url")).strip()
	if not source:
		return None

	media_type = cstr(row.get("media_type")).strip()
	detected_kind = get_media_kind(source)
	render_type = detected_kind if detected_kind in ("Image", "Video", "YouTube") else "URL"

	return frappe._dict(
		{
			"media_type": media_type or render_type,
			"render_type": render_type,
			"source": source,
			"embed_url": get_youtube_embed_url(source) if render_type == "YouTube" else "",
			"caption": cstr(row.get("caption")).strip(),
			"sort_order": row.get("sort_order") or 0,
		}
	)
