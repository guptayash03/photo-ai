import io
import pytest
from PIL import Image

from app.utils.image_utils import generate_thumbnail, extract_exif


def _create_test_image(size: tuple = (1000, 800)) -> bytes:
    img = Image.new("RGB", size, (100, 150, 200))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_generate_thumbnail_resizes():
    image_bytes = _create_test_image(size=(2000, 1500))
    thumbnail_bytes = generate_thumbnail(image_bytes, max_size=400)

    thumb = Image.open(io.BytesIO(thumbnail_bytes))
    assert thumb.width <= 400
    assert thumb.height <= 400


def test_generate_thumbnail_preserves_aspect_ratio():
    image_bytes = _create_test_image(size=(1000, 500))
    thumbnail_bytes = generate_thumbnail(image_bytes, max_size=200)

    thumb = Image.open(io.BytesIO(thumbnail_bytes))
    assert thumb.width == 200
    assert thumb.height == 100


def test_generate_thumbnail_jpeg_output():
    image_bytes = _create_test_image()
    thumbnail_bytes = generate_thumbnail(image_bytes)

    thumb = Image.open(io.BytesIO(thumbnail_bytes))
    assert thumb.format == "JPEG"


def test_generate_thumbnail_smaller_than_original():
    image_bytes = _create_test_image(size=(2000, 2000))
    thumbnail_bytes = generate_thumbnail(image_bytes)
    assert len(thumbnail_bytes) < len(image_bytes)


def test_extract_exif_no_exif():
    image_bytes = _create_test_image()
    result = extract_exif(image_bytes)
    # Simple generated images don't have EXIF
    assert result is None or result == {}


def test_generate_thumbnail_rgba_input():
    img = Image.new("RGBA", (500, 500), (100, 150, 200, 128))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    thumbnail_bytes = generate_thumbnail(image_bytes)
    thumb = Image.open(io.BytesIO(thumbnail_bytes))
    assert thumb.mode == "RGB"
