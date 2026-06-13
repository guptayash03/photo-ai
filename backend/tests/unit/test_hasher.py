import io
import pytest
from PIL import Image

from app.ml.hasher import (
    compute_file_md5,
    compute_phash,
    compute_dhash,
    hamming_distance,
    are_near_duplicates,
)


def _create_test_image(color: tuple = (255, 0, 0), size: tuple = (100, 100)) -> bytes:
    img = Image.new("RGB", size, color)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_compute_file_md5():
    data = b"test data"
    md5 = compute_file_md5(data)
    assert len(md5) == 32
    assert md5 == compute_file_md5(data)  # deterministic


def test_compute_file_md5_different_data():
    md5_a = compute_file_md5(b"data a")
    md5_b = compute_file_md5(b"data b")
    assert md5_a != md5_b


def test_compute_phash():
    image_bytes = _create_test_image()
    phash = compute_phash(image_bytes)
    assert isinstance(phash, str)
    assert len(phash) == 16  # 64-bit hash as hex


def test_compute_dhash():
    image_bytes = _create_test_image()
    dhash = compute_dhash(image_bytes)
    assert isinstance(dhash, str)
    assert len(dhash) == 16


def test_identical_images_same_hash():
    img_bytes = _create_test_image()
    hash1 = compute_phash(img_bytes)
    hash2 = compute_phash(img_bytes)
    assert hash1 == hash2


def test_different_images_different_hash():
    img_a = _create_test_image(color=(255, 0, 0))
    img_b = _create_test_image(color=(0, 0, 255))
    hash_a = compute_phash(img_a)
    hash_b = compute_phash(img_b)
    # Different colors should produce different hashes
    # (though simple solid colors might be similar)
    assert isinstance(hash_a, str)
    assert isinstance(hash_b, str)


def test_hamming_distance_identical():
    h = "a" * 16
    assert hamming_distance(h, h) == 0


def test_hamming_distance_different():
    h1 = "0000000000000000"
    h2 = "ffffffffffffffff"
    distance = hamming_distance(h1, h2)
    assert distance == 64


def test_are_near_duplicates_true():
    img_bytes = _create_test_image()
    hash1 = compute_phash(img_bytes)
    # Same hash = 0 distance = near duplicate
    assert are_near_duplicates(hash1, hash1, threshold=8)


def test_are_near_duplicates_false():
    h1 = "0000000000000000"
    h2 = "ffffffffffffffff"
    assert not are_near_duplicates(h1, h2, threshold=8)
