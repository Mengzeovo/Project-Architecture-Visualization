from __future__ import annotations

import hashlib
from pathlib import Path


def normalize_rel_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}:{digest}"


def sanitize_d2_identifier(raw: str) -> str:
    cleaned = []
    for char in raw:
        if char.isalnum() or char in {"_", "-"}:
            cleaned.append(char)
        else:
            cleaned.append("_")
    value = "".join(cleaned).strip("_")
    if not value:
        return "node"
    if value[0].isdigit():
        return f"n_{value}"
    return value
