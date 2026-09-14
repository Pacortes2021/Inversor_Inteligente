"""Content-addressed immutable raw payload storage."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class StoredBlob:
    sha256: str
    relative_path: str
    size_bytes: int


class RawStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.raw_root = self.root / "raw"

    def put(self, content: bytes) -> StoredBlob:
        digest = hashlib.sha256(content).hexdigest()
        relative = Path("raw") / digest[:2] / digest
        destination = self.root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != content:
                raise RuntimeError("content-addressed path hash mismatch")
            return StoredBlob(digest, relative.as_posix(), len(content))
        descriptor, temporary_name = tempfile.mkstemp(prefix=".incoming-", dir=destination.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            try:
                # A hard link publishes the completed file atomically without
                # ever replacing an immutable blob created by another writer.
                os.link(temporary, destination)
            except FileExistsError:
                if destination.read_bytes() != content:
                    raise RuntimeError("content-addressed path hash mismatch")
        finally:
            if temporary.exists():
                temporary.unlink()
        return StoredBlob(digest, relative.as_posix(), len(content))

    def read(self, sha256: str) -> bytes:
        if not SHA256_PATTERN.fullmatch(sha256):
            raise ValueError("invalid SHA-256 identifier")
        path = self.raw_root / sha256[:2] / sha256
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != sha256:
            raise RuntimeError("stored payload hash mismatch")
        return content
