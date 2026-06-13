import io
from datetime import datetime, timezone
from typing import Optional

from PIL import Image, ExifTags


def generate_thumbnail(image_bytes: bytes, max_size: int = 400) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((max_size, max_size), Image.LANCZOS)

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85, optimize=True)
    return buffer.getvalue()


def extract_exif(image_bytes: bytes) -> Optional[dict]:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif_data = img._getexif()
        if not exif_data:
            return None

        exif = {}
        for tag_id, value in exif_data.items():
            tag = ExifTags.TAGS.get(tag_id, tag_id)
            exif[tag] = value

        result = {}

        # Date taken
        date_str = exif.get("DateTimeOriginal") or exif.get("DateTime")
        if date_str:
            try:
                result["taken_at"] = datetime.strptime(
                    date_str, "%Y:%m:%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

        # Camera info
        result["camera_make"] = exif.get("Make")
        result["camera_model"] = exif.get("Model")

        # GPS
        gps_info = exif.get("GPSInfo")
        if gps_info:
            lat = _convert_gps_to_decimal(gps_info.get(2), gps_info.get(1))
            lon = _convert_gps_to_decimal(gps_info.get(4), gps_info.get(3))
            if lat is not None:
                result["gps_latitude"] = lat
            if lon is not None:
                result["gps_longitude"] = lon

        return result if result else None
    except Exception:
        return None


def _convert_gps_to_decimal(coords, ref) -> Optional[float]:
    if not coords or not ref:
        return None
    try:
        degrees = float(coords[0])
        minutes = float(coords[1])
        seconds = float(coords[2])
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal
    except (TypeError, IndexError, ValueError):
        return None
