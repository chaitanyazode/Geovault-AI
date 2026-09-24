import hashlib

def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 checksum of a file for duplicate detection and idempotency."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
