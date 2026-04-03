from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib

from ..models import Edge, EvidenceRef, Node
from ..utils import normalize_rel_path
from .base import ExtractionContext, Extractor


class DependencyMetadataExtractor(Extractor):
    name = "dependency-metadata"

    def run(self, context: ExtractionContext) -> None:
        for package_json in context.scan.package_json_files:
            self._extract_package_json(context, package_json)
        for pyproject in context.scan.pyproject_files:
            self._extract_pyproject(context, pyproject)
        for requirements in context.scan.requirements_files:
            self._extract_requirements(context, requirements)
        for manifest in context.scan.generic_manifest_files:
            self._extract_generic_manifest(context, manifest)

    def _extract_package_json(self, context: ExtractionContext, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        container_id = context.container_id_for(path)
        rel = normalize_rel_path(path, context.root)

        dependency_sections = [
            "dependencies",
            "devDependencies",
            "peerDependencies",
            "optionalDependencies",
        ]
        for section in dependency_sections:
            dependencies = data.get(section)
            if not isinstance(dependencies, dict):
                continue
            for package_name in dependencies.keys():
                package_node_id = f"package:{package_name}"
                evidence = EvidenceRef(file=rel, line=1, rule_id=f"node.package_json.{section}")
                context.graph.add_node(
                    Node(
                        id=package_node_id,
                        type="package",
                        name=package_name,
                        confidence=1.0,
                        evidence_refs=[evidence],
                        tags=["npm"],
                    )
                )
                context.graph.add_edge(
                    Edge(
                        source=container_id,
                        target=package_node_id,
                        type="depends_on",
                        confidence=0.95,
                        evidence_refs=[evidence],
                        metadata={"section": section},
                    )
                )

    def _extract_pyproject(self, context: ExtractionContext, path: Path) -> None:
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return

        container_id = context.container_id_for(path)
        rel = normalize_rel_path(path, context.root)

        dependencies: set[str] = set()
        project = data.get("project")
        if isinstance(project, dict):
            values = project.get("dependencies")
            if isinstance(values, list):
                dependencies.update(_normalize_python_dependency(item) for item in values)
            optional = project.get("optional-dependencies")
            if isinstance(optional, dict):
                for value in optional.values():
                    if isinstance(value, list):
                        dependencies.update(_normalize_python_dependency(item) for item in value)

        poetry = data.get("tool", {}).get("poetry") if isinstance(data.get("tool"), dict) else None
        if isinstance(poetry, dict):
            for section_name in ["dependencies", "group"]:
                section = poetry.get(section_name)
                if section_name == "dependencies" and isinstance(section, dict):
                    dependencies.update(name for name in section.keys() if name != "python")
                if section_name == "group" and isinstance(section, dict):
                    for group_data in section.values():
                        deps = group_data.get("dependencies") if isinstance(group_data, dict) else None
                        if isinstance(deps, dict):
                            dependencies.update(deps.keys())

        for package_name in sorted(item for item in dependencies if item):
            package_node_id = f"package:{package_name}"
            evidence = EvidenceRef(file=rel, line=1, rule_id="node.pyproject")
            context.graph.add_node(
                Node(
                    id=package_node_id,
                    type="package",
                    name=package_name,
                    confidence=1.0,
                    evidence_refs=[evidence],
                    tags=["python"],
                )
            )
            context.graph.add_edge(
                Edge(
                    source=container_id,
                    target=package_node_id,
                    type="depends_on",
                    confidence=0.95,
                    evidence_refs=[evidence],
                )
            )

    def _extract_requirements(self, context: ExtractionContext, path: Path) -> None:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return

        container_id = context.container_id_for(path)
        rel = normalize_rel_path(path, context.root)
        for index, line in enumerate(lines, start=1):
            package_name = _normalize_python_dependency(line)
            if not package_name:
                continue
            package_node_id = f"package:{package_name}"
            evidence = EvidenceRef(file=rel, line=index, rule_id="node.requirements")
            context.graph.add_node(
                Node(
                    id=package_node_id,
                    type="package",
                    name=package_name,
                    confidence=1.0,
                    evidence_refs=[evidence],
                    tags=["python"],
                )
            )
            context.graph.add_edge(
                Edge(
                    source=container_id,
                    target=package_node_id,
                    type="depends_on",
                    confidence=0.95,
                    evidence_refs=[evidence],
                )
            )

    def _extract_generic_manifest(self, context: ExtractionContext, path: Path) -> None:
        rel = normalize_rel_path(path, context.root)
        container_id = context.container_id_for(path)
        manifest_name = path.name.lower()
        evidence = EvidenceRef(file=rel, line=1, rule_id="node.manifest")

        ecosystem, package_name = _classify_manifest(manifest_name, path)
        package_node_id = f"package:{package_name}"

        context.graph.add_node(
            Node(
                id=package_node_id,
                type="package",
                name=package_name,
                confidence=0.85,
                evidence_refs=[evidence],
                tags=[ecosystem],
            )
        )
        context.graph.add_edge(
            Edge(
                source=container_id,
                target=package_node_id,
                type="depends_on",
                confidence=0.8,
                evidence_refs=[evidence],
                metadata={"manifest": manifest_name},
            )
        )


_PY_DEP_RE = re.compile(r"^[A-Za-z0-9_.-]+")


def _normalize_python_dependency(raw: str) -> str | None:
    value = raw.strip()
    if not value or value.startswith("#") or value.startswith("-"):
        return None
    if ";" in value:
        value = value.split(";", 1)[0].strip()
    match = _PY_DEP_RE.match(value)
    if not match:
        return None
    return match.group(0).lower().replace("_", "-")


def _classify_manifest(manifest_name: str, path: Path) -> tuple[str, str]:
    parent = path.parent.name.lower()
    if manifest_name in {
        "cmakelists.txt",
        "conanfile.txt",
        "conanfile.py",
        "meson.build",
        "meson.options",
        "vcpkg.json",
    }:
        return "cpp", f"cpp-target:{parent}"
    if manifest_name == "go.mod":
        return "go", f"go-module:{parent}"
    if manifest_name == "cargo.toml":
        return "rust", f"rust-crate:{parent}"
    if manifest_name in {"pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"}:
        return "jvm", f"jvm-module:{parent}"
    if manifest_name == "composer.json":
        return "php", f"php-package:{parent}"
    if manifest_name == "gemfile":
        return "ruby", f"ruby-app:{parent}"
    return "generic", f"manifest:{manifest_name}:{parent}"
