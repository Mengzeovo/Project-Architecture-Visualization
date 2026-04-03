from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

from ..constants import HTTP_METHODS
from ..models import Edge, EvidenceRef, Node
from ..utils import normalize_rel_path
from .base import ExtractionContext, Extractor


class PythonExtractor(Extractor):
    name = "python"

    def run(self, context: ExtractionContext) -> None:
        file_to_module_id: dict[Path, str] = {}
        file_index = {path.resolve(): path for path in context.scan.python_files}

        for path in context.scan.python_files:
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
                    tags=["python"],
                    confidence=1.0,
                    evidence_refs=[EvidenceRef(file=rel, line=1, rule_id="node.python_file")],
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

        for path in context.scan.python_files:
            self._process_file(context, path, file_to_module_id, file_index)

    def _process_file(
        self,
        context: ExtractionContext,
        path: Path,
        file_to_module_id: dict[Path, str],
        file_index: dict[Path, Path],
    ) -> None:
        rel = normalize_rel_path(path, context.root)
        source_module_id = file_to_module_id[path.resolve()]
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except (OSError, UnicodeDecodeError, SyntaxError):
            return

        self._extract_import_edges(context, tree, path, rel, source_module_id, file_to_module_id, file_index)
        self._extract_fastapi_routes(context, tree, path, rel)
        self._extract_http_and_data_edges(context, tree, rel, source_module_id)

    def _extract_import_edges(
        self,
        context: ExtractionContext,
        tree: ast.AST,
        source_path: Path,
        rel: str,
        source_module_id: str,
        file_to_module_id: dict[Path, str],
        file_index: dict[Path, Path],
    ) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = _resolve_python_import(
                        source_path=source_path,
                        module=alias.name,
                        level=0,
                        context=context,
                        file_index=file_index,
                    )
                    if not target:
                        continue
                    target_module_id = file_to_module_id.get(target.resolve())
                    if not target_module_id:
                        continue
                    evidence = EvidenceRef(file=rel, line=node.lineno, rule_id="edge.imports.python")
                    context.graph.add_edge(
                        Edge(
                            source=source_module_id,
                            target=target_module_id,
                            type="imports",
                            confidence=1.0,
                            evidence_refs=[evidence],
                        )
                    )

            if isinstance(node, ast.ImportFrom):
                module = node.module
                level = node.level or 0
                if not module and level == 0:
                    continue

                target = _resolve_python_import(
                    source_path=source_path,
                    module=module,
                    level=level,
                    context=context,
                    file_index=file_index,
                    imported_names=[alias.name for alias in node.names],
                )
                if not target:
                    continue
                target_module_id = file_to_module_id.get(target.resolve())
                if not target_module_id:
                    continue
                evidence = EvidenceRef(file=rel, line=node.lineno, rule_id="edge.imports.python")
                context.graph.add_edge(
                    Edge(
                        source=source_module_id,
                        target=target_module_id,
                        type="imports",
                        confidence=1.0,
                        evidence_refs=[evidence],
                    )
                )

    def _extract_fastapi_routes(
        self,
        context: ExtractionContext,
        tree: ast.AST,
        path: Path,
        rel: str,
    ) -> None:
        container_id = context.container_id_for(path)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                route = _extract_python_route_from_decorator(decorator)
                if not route:
                    continue
                method, endpoint = route
                endpoint_id = f"endpoint:{container_id}:{method}:{endpoint}"
                evidence = EvidenceRef(file=rel, line=node.lineno, rule_id="node.fastapi.route")
                context.graph.add_node(
                    Node(
                        id=endpoint_id,
                        type="api_endpoint",
                        name=f"{method} {endpoint}",
                        confidence=0.95,
                        evidence_refs=[evidence],
                        tags=["python", "fastapi"],
                        metadata={"container_id": container_id},
                    )
                )
                context.graph.add_edge(
                    Edge(
                        source=container_id,
                        target=endpoint_id,
                        type="exposes",
                        confidence=0.95,
                        evidence_refs=[evidence],
                    )
                )

    def _extract_http_and_data_edges(
        self,
        context: ExtractionContext,
        tree: ast.AST,
        rel: str,
        source_module_id: str,
    ) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            callee = _call_name(node.func)
            if not callee:
                continue

            if callee.startswith(("requests.", "httpx.", "aiohttp.")):
                external_id = "external_api:http"
                evidence = EvidenceRef(file=rel, line=node.lineno, rule_id="edge.http.python")
                context.graph.add_node(
                    Node(
                        id=external_id,
                        type="external_api",
                        name="External HTTP APIs",
                        confidence=0.7,
                        evidence_refs=[evidence],
                    )
                )
                context.graph.add_edge(
                    Edge(
                        source=source_module_id,
                        target=external_id,
                        type="http",
                        confidence=0.7,
                        evidence_refs=[evidence],
                    )
                )

            if callee.startswith(("sqlalchemy.", "psycopg2.", "sqlite3.", "pymongo.", "redis.")):
                infra_id, infra_name, edge_type = _infer_python_data_node(callee)
                evidence = EvidenceRef(file=rel, line=node.lineno, rule_id="edge.data.python")
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


def _extract_python_route_from_decorator(node: ast.AST) -> tuple[str, str] | None:
    if not isinstance(node, ast.Call):
        return None
    if not isinstance(node.func, ast.Attribute):
        return None
    method = node.func.attr.lower()
    if method not in HTTP_METHODS:
        return None
    if not node.args:
        return method.upper(), "/"
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return method.upper(), first.value
    return method.upper(), "/"


def _resolve_python_import(
    source_path: Path,
    module: str | None,
    level: int,
    context: ExtractionContext,
    file_index: dict[Path, Path],
    imported_names: Iterable[str] | None = None,
) -> Path | None:
    base_dir = source_path.parent
    candidate_modules: list[str] = []

    if level > 0:
        for _ in range(max(level - 1, 0)):
            base_dir = base_dir.parent
    if module:
        candidate_modules.append(module)

    imported_names = list(imported_names or [])
    if module and imported_names:
        candidate_modules.extend(f"{module}.{name}" for name in imported_names if name != "*")
    if not module and imported_names:
        candidate_modules.extend(name for name in imported_names if name != "*")

    roots = [context.root, context.container_root_for(source_path)]
    search_dirs = [base_dir, *roots]

    for module_name in candidate_modules:
        parts = module_name.split(".") if module_name else []
        if not parts:
            continue
        for directory in search_dirs:
            by_file = directory.joinpath(*parts).with_suffix(".py")
            by_package = directory.joinpath(*parts, "__init__.py")
            for candidate in [by_file, by_package]:
                resolved = candidate.resolve()
                if resolved in file_index:
                    return file_index[resolved]
    return None


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        if not parent:
            return node.attr
        return f"{parent}.{node.attr}"
    return None


def _infer_python_data_node(callee: str) -> tuple[str, str, str]:
    if callee.startswith(("redis.",)):
        return "cache:redis", "Redis", "reads"
    if callee.startswith(("pymongo.",)):
        return "database:mongodb", "MongoDB", "reads"
    if callee.startswith(("sqlite3.",)):
        return "database:sqlite", "SQLite", "reads"
    return "database:sql", "SQL Database", "reads"
