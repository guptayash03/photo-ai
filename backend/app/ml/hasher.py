import hashlib
import io

import imagehash
from PIL import Image


def compute_file_md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def compute_phash(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    return str(imagehash.phash(image))


def compute_dhash(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    return str(imagehash.dhash(image))


def compute_average_hash(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    return str(imagehash.average_hash(image))


def hamming_distance(hash1: str, hash2: str) -> int:
    h1 = imagehash.hex_to_hash(hash1)
    h2 = imagehash.hex_to_hash(hash2)
    return h1 - h2


def are_near_duplicates(hash1: str, hash2: str, threshold: int = 8) -> bool:
    return hamming_distance(hash1, hash2) <= threshold
