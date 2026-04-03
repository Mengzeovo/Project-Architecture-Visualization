from __future__ import annotations

from pathlib import Path

from .scanner import ScanResult


def _promote_entrypoint_parent(path: Path, root: Path) -> Path:
    parent = path.parent
    if parent.name in {"src", "app"} and parent.parent != root:
        return parent.parent
    return parent


def discover_service_roots(scan: ScanResult) -> list[Path]:
    root = scan.root
    candidates: set[Path] = {root}

    for entrypoint in scan.entrypoint_candidates:
        candidates.add(_promote_entrypoint_parent(entrypoint, root))

    for manifest in [
        *scan.package_json_files,
        *scan.pyproject_files,
        *scan.requirements_files,
        *scan.generic_manifest_files,
    ]:
        if manifest.parent != root:
            candidates.add(manifest.parent)

    language_files = [
        *scan.python_files,
        *scan.ts_files,
        *scan.go_files,
        *scan.java_files,
        *scan.csharp_files,
        *scan.cpp_files,
        *scan.rust_files,
        *scan.php_files,
        *scan.ruby_files,
    ]
    for file_path in language_files:
        try:
            relative_parts = file_path.relative_to(root).parts
        except ValueError:
            continue
        if len(relative_parts) < 2:
            continue
        if relative_parts[0] in {"apps", "services", "packages"} and len(relative_parts) >= 2:
            candidates.add(root / relative_parts[0] / relative_parts[1])

    top_level_code_dirs = {
        root / file_path.relative_to(root).parts[0]
        for file_path in language_files
        if len(file_path.relative_to(root).parts) > 1
    }
    if len(top_level_code_dirs) > 1:
        candidates.update(top_level_code_dirs)

    valid_candidates = {path for path in candidates if path.exists() and path.is_dir()}
    if root not in valid_candidates:
        valid_candidates.add(root)
    return sorted(valid_candidates, key=lambda item: (len(item.parts), item.as_posix()))
