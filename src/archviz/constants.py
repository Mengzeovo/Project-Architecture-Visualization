from __future__ import annotations

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
    "target",
    "coverage",
    ".next",
    ".nuxt",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".mypy_cache",
    ".pytest_cache",
}

PYTHON_EXTENSIONS = {".py"}
TS_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".mts", ".cts"}
GO_EXTENSIONS = {".go"}
JAVA_EXTENSIONS = {".java", ".kt", ".kts"}
CSHARP_EXTENSIONS = {".cs"}
CPLUSPLUS_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".ipp",
    ".inl",
}
RUST_EXTENSIONS = {".rs"}
PHP_EXTENSIONS = {".php"}
RUBY_EXTENSIONS = {".rb"}

GENERIC_MANIFEST_BASENAMES = {
    "go.mod",
    "cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "cmakelists.txt",
    "conanfile.txt",
    "conanfile.py",
    "meson.build",
    "meson.options",
    "vcpkg.json",
    "composer.json",
    "gemfile",
}

ENTRYPOINT_BASENAMES = {
    "main.py",
    "app.py",
    "wsgi.py",
    "asgi.py",
    "manage.py",
    "main.ts",
    "main.js",
    "index.ts",
    "index.js",
    "app.ts",
    "app.js",
    "server.ts",
    "server.js",
}

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
