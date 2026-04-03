from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

from .constants import (
    CPLUSPLUS_EXTENSIONS,
    CSHARP_EXTENSIONS,
    ENTRYPOINT_BASENAMES,
    GENERIC_MANIFEST_BASENAMES,
    GO_EXTENSIONS,
    IGNORED_DIRS,
    JAVA_EXTENSIONS,
    PHP_EXTENSIONS,
    PYTHON_EXTENSIONS,
    RUBY_EXTENSIONS,
    RUST_EXTENSIONS,
    TS_EXTENSIONS,
)


@dataclass(slots=True)
class ScanResult:
    root: Path
    python_files: list[Path] = field(default_factory=list)
    ts_files: list[Path] = field(default_factory=list)
    go_files: list[Path] = field(default_factory=list)
    java_files: list[Path] = field(default_factory=list)
    csharp_files: list[Path] = field(default_factory=list)
    cpp_files: list[Path] = field(default_factory=list)
    rust_files: list[Path] = field(default_factory=list)
    php_files: list[Path] = field(default_factory=list)
    ruby_files: list[Path] = field(default_factory=list)
    package_json_files: list[Path] = field(default_factory=list)
    pyproject_files: list[Path] = field(default_factory=list)
    requirements_files: list[Path] = field(default_factory=list)
    generic_manifest_files: list[Path] = field(default_factory=list)
    docker_files: list[Path] = field(default_factory=list)
    compose_files: list[Path] = field(default_factory=list)
    entrypoint_candidates: list[Path] = field(default_factory=list)


def should_skip_dir(path: Path) -> bool:
    return path.name in IGNORED_DIRS


def scan_project(root: Path) -> ScanResult:
    result = ScanResult(root=root)
    for current_root, dirnames, filenames in os.walk(root, topdown=True):
        current_root_path = Path(current_root)
        dirnames[:] = [name for name in dirnames if name not in IGNORED_DIRS]
        for filename in filenames:
            path = current_root_path / filename
            suffix = path.suffix.lower()
            lower_name = filename.lower()

            if suffix in PYTHON_EXTENSIONS:
                result.python_files.append(path)
            if suffix in TS_EXTENSIONS:
                result.ts_files.append(path)
            if suffix in GO_EXTENSIONS:
                result.go_files.append(path)
            if suffix in JAVA_EXTENSIONS:
                result.java_files.append(path)
            if suffix in CSHARP_EXTENSIONS:
                result.csharp_files.append(path)
            if suffix in CPLUSPLUS_EXTENSIONS:
                result.cpp_files.append(path)
            if suffix in RUST_EXTENSIONS:
                result.rust_files.append(path)
            if suffix in PHP_EXTENSIONS:
                result.php_files.append(path)
            if suffix in RUBY_EXTENSIONS:
                result.ruby_files.append(path)

            if lower_name == "package.json":
                result.package_json_files.append(path)
            if lower_name == "pyproject.toml":
                result.pyproject_files.append(path)
            if lower_name in {"requirements.txt", "requirements-dev.txt"}:
                result.requirements_files.append(path)
            if lower_name in GENERIC_MANIFEST_BASENAMES:
                result.generic_manifest_files.append(path)
            if lower_name == "dockerfile" or lower_name.startswith("dockerfile."):
                result.docker_files.append(path)
            if lower_name in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}:
                result.compose_files.append(path)
            if lower_name in ENTRYPOINT_BASENAMES:
                result.entrypoint_candidates.append(path)

    result.python_files.sort()
    result.ts_files.sort()
    result.go_files.sort()
    result.java_files.sort()
    result.csharp_files.sort()
    result.cpp_files.sort()
    result.rust_files.sort()
    result.php_files.sort()
    result.ruby_files.sort()
    result.package_json_files.sort()
    result.pyproject_files.sort()
    result.requirements_files.sort()
    result.generic_manifest_files.sort()
    result.docker_files.sort()
    result.compose_files.sort()
    result.entrypoint_candidates.sort()
    return result
