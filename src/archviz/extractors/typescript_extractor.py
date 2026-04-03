from __future__ import annotations

import re
from pathlib import Path

from ..models import Edge, EvidenceRef, Node
from ..utils import normalize_rel_path
from .base import ExtractionContext, Extractor


IMPORT_RE = re.compile(
    r"(?:import\s+(?:[^\n;]*?)\s+from\s+|import\s*\()\s*[\"']([^\"']+)[\"']"
)
REQUIRE_RE = re.compile(r"require\(\s*[\"']([^\"']+)[\"']\s*\)")
EXPRESS_ROUTE_RE = re.compile(
    r"\b(?:app|router)\.(get|post|put|patch|delete|options|head)\s*\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
HTTP_CALL_RE = re.compile(r"\b(?:axios|fetch|got)\b|\bhttps?\.request\b")
DATA_CALL_RE = re.compile(
    r"\b(?:prisma\.|typeorm\.|mongoose\.|mongodb\.|redis\.|ioredis\.|kafkajs\.|amqplib\.)"
)


class TypeScriptExtractor(Extractor):
    name = "typescript"

    def run(self, context: ExtractionContext) -> None:
        file_to_module_id: dict[Path, str] = {}
        ts_index = {path.resolve(): path for path in context.scan.ts_files}

        for path in context.scan.ts_files:
            module_id = self._module_id_for(path, context)
            file_to_module_id[path.resolve()] = module_id
            rel = normalize_rel_path(path, context.root)
            container_id = context.container_id_for(path)
            context.graph.add_node(
                Node(
                    id=module_id,
                    type="module",
                    name=rel,
                    path=rel,
                    tags=["typescript"],
                    confidence=1.0,
                    evidence_refs=[EvidenceRef(file=rel, line=1, rule_id="node.ts_file")],
                    metadata={"container_id": container_id},
                )
            )
            context.graph.add_edge(
                Edge(
                    source=container_id,
                    target=module_id,
                    type="contains",
                    confidence=1.0,
                    evidence_refs=[EvidenceRef(file=rel, line=1, rule_id="edge.contains")],
                )
            )

        for path in context.scan.ts_files:
            self._process_file(context, path, file_to_module_id, ts_index)

    def _process_file(
        self,
        context: ExtractionContext,
        path: Path,
        file_to_module_id: dict[Path, str],
        ts_index: dict[Path, Path],
    ) -> None:
        rel = normalize_rel_path(path, context.root)
        source_module_id = file_to_module_id[path.resolve()]

        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return

        lines = text.splitlines()
        self._extract_import_edges(context, path, rel, source_module_id, file_to_module_id, ts_index, lines)
        self._extract_express_routes(context, path, rel, lines)
        self._extract_http_and_data_edges(context, rel, source_module_id, lines)

    def _extract_import_edges(
        self,
        context: ExtractionContext,
        source_path: Path,
        rel: str,
        source_module_id: str,
        file_to_module_id: dict[Path, str],
        ts_index: dict[Path, Path],
        lines: list[str],
    ) -> None:
        for index, line in enumerate(lines, start=1):
            specifiers = [*IMPORT_RE.findall(line), *REQUIRE_RE.findall(line)]
            for specifier in specifiers:
                target = _resolve_ts_import(source_path, specifier, context, ts_index)
                if not target:
                    continue
                target_id = file_to_module_id.get(target.resolve())
                if not target_id:
                    continue
                evidence = EvidenceRef(file=rel, line=index, rule_id="edge.imports.ts")
                context.graph.add_edge(
                    Edge(
                        source=source_module_id,
                        target=target_id,
                        type="imports",
                        confidence=1.0,
                        evidence_refs=[evidence],
                    )
                )

    def _extract_express_routes(
        self,
        context: ExtractionContext,
        path: Path,
        rel: str,
        lines: list[str],
    ) -> None:
        container_id = context.container_id_for(path)
        for index, line in enumerate(lines, start=1):
            match = EXPRESS_ROUTE_RE.search(line)
            if not match:
                continue
            method, endpoint = match.group(1).upper(), match.group(2)
            endpoint_id = f"endpoint:{container_id}:{method}:{endpoint}"
            evidence = EvidenceRef(file=rel, line=index, rule_id="node.express.route")
            context.graph.add_node(
                Node(
                    id=endpoint_id,
                    type="api_endpoint",
                    name=f"{method} {endpoint}",
                    confidence=0.9,
                    evidence_refs=[evidence],
                    tags=["typescript", "express"],
                    metadata={"container_id": container_id},
                )
            )
            context.graph.add_edge(
                Edge(
                    source=container_id,
                    target=endpoint_id,
                    type="exposes",
                    confidence=0.9,
                    evidence_refs=[evidence],
                )
            )

    def _extract_http_and_data_edges(
        self,
        context: ExtractionContext,
        rel: str,
        source_module_id: str,
        lines: list[str],
    ) -> None:
        for index, line in enumerate(lines, start=1):
            if HTTP_CALL_RE.search(line):
                evidence = EvidenceRef(file=rel, line=index, rule_id="edge.http.ts")
                context.graph.add_node(
                    Node(
                        id="external_api:http",
                        type="external_api",
                        name="External HTTP APIs",
                        confidence=0.7,
                        evidence_refs=[evidence],
                    )
                )
                context.graph.add_edge(
                    Edge(
                        source=source_module_id,
                        target="external_api:http",
                        type="http",
                        confidence=0.7,
                        evidence_refs=[evidence],
                    )
                )

            data_match = DATA_CALL_RE.search(line)
            if data_match:
                infra_id, infra_name, edge_type = _infer_ts_data_node(data_match.group(0))
                evidence = EvidenceRef(file=rel, line=index, rule_id="edge.data.ts")
                context.graph.add_node(
                    Node(
                        id=infra_id,
                        type="database" if edge_type in {"reads", "writes"} else "queue",
                        name=infra_name,
                        confidence=0.75,
                        evidence_refs=[evidence],
                    )
                )
                context.graph.add_edge(
                    Edge(
                        source=source_module_id,
                        target=infra_id,
                        type=edge_type,
                        confidence=0.75,
                        evidence_refs=[evidence],
                    )
                )

    def _module_id_for(self, path: Path, context: ExtractionContext) -> str:
        rel = normalize_rel_path(path, context.root)
        return f"module:{rel}"


def _resolve_ts_import(
    source_path: Path,
    specifier: str,
    context: ExtractionContext,
    ts_index: dict[Path, Path],
) -> Path | None:
    if not specifier.startswith((".", "/")):
        return None

    base = source_path.parent
    if specifier.startswith("/"):
        candidate_base = context.container_root_for(source_path)
        raw_target = candidate_base / specifier.lstrip("/")
    else:
        raw_target = base / specifier

    candidates = [
        raw_target,
        raw_target.with_suffix(".ts"),
        raw_target.with_suffix(".tsx"),
        raw_target.with_suffix(".js"),
        raw_target.with_suffix(".jsx"),
        raw_target / "index.ts",
        raw_target / "index.tsx",
        raw_target / "index.js",
        raw_target / "index.jsx",
    ]

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in ts_index:
            return ts_index[resolved]
    return None


def _infer_ts_data_node(matched: str) -> tuple[str, str, str]:
    value = matched.lower()
    if "redis" in value:
        return "cache:redis", "Redis", "reads"
    if "kafkajs" in value:
        return "queue:kafka", "Kafka", "publishes"
    if "amqplib" in value:
        return "queue:rabbitmq", "RabbitMQ", "publishes"
    if "mongoose" in value or "mongodb" in value:
        return "database:mongodb", "MongoDB", "reads"
    return "database:sql", "SQL Database", "reads"
