"""Parse Python source files into per-file facts using the stdlib ``ast``.

For each file we record:
  * definitions: functions, classes and methods (qualified name + line)
  * calls: which callee name is called, from which enclosing definition, at which line
  * imports: modules imported and names bound by ``from x import y``
"""

from __future__ import annotations

import ast
import fnmatch
import os
from dataclasses import dataclass, field

SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv", "env",
    ".env", ".tox", ".nox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "build", "dist", "site-packages", ".eggs",
}


@dataclass
class Definition:
    qualname: str          # "func", "Class", "Class.method"
    kind: str              # "function" | "class" | "method"
    line: int


@dataclass
class Call:
    caller: str            # qualname of enclosing definition, "" for module level
    name: str              # bare callee name (last attribute segment)
    line: int
    receiver: str = ""     # "self", a module alias, or "" for plain calls


@dataclass
class FileFacts:
    path: str                                   # repo-relative, "/" separated
    module: str                                 # dotted module name
    definitions: list[Definition] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)          # dotted modules
    from_names: dict[str, str] = field(default_factory=dict)  # local name -> "module:name"
    error: str | None = None


def path_to_module(rel_path: str) -> str:
    parts = rel_path[:-3].split("/") if rel_path.endswith(".py") else rel_path.split("/")
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    # drop a leading "src" layout dir so `src/pkg/mod.py` is `pkg.mod`
    if parts and parts[0] == "src" and len(parts) > 1:
        parts = parts[1:]
    return ".".join(parts)


class _Visitor(ast.NodeVisitor):
    def __init__(self, facts: FileFacts):
        self.f = facts
        self.scope: list[tuple[str, str]] = []   # (name, kind)

    # -- helpers -------------------------------------------------------
    def _qual(self, name: str) -> str:
        return ".".join([s for s, _ in self.scope] + [name])

    def _enclosing_def(self) -> str:
        return ".".join(s for s, _ in self.scope)

    def _resolve_relative(self, module: str | None, level: int) -> str:
        if not level:
            return module or ""
        base = self.f.module.split(".")
        # a package's __init__ is itself the package
        if not self.f.path.endswith("__init__.py"):
            base = base[:-1]
        if level > 1:
            base = base[: len(base) - (level - 1)] if level - 1 <= len(base) else []
        return ".".join([*base, module] if module else base)

    # -- definitions ---------------------------------------------------
    def _visit_def(self, node, kind_default: str):
        in_class = bool(self.scope) and self.scope[-1][1] == "class"
        kind = "method" if (kind_default == "function" and in_class) else kind_default
        self.f.definitions.append(Definition(self._qual(node.name), kind, node.lineno))
        for d in getattr(node, "decorator_list", []):
            self.visit(d)
        self.scope.append((node.name, "class" if kind_default == "class" else "function"))
        for child in node.body:
            self.visit(child)
        if kind_default == "class":
            for b in node.bases:
                self.visit(b)
        else:
            self.visit(node.args)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        self._visit_def(node, "function")

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._visit_def(node, "class")

    # -- imports -------------------------------------------------------
    def visit_Import(self, node):
        for a in node.names:
            self.f.imports.append(a.name)
            self.f.from_names[a.asname or a.name.split(".")[0]] = a.name + ":"

    def visit_ImportFrom(self, node):
        mod = self._resolve_relative(node.module, node.level)
        if mod:
            self.f.imports.append(mod)
        for a in node.names:
            if a.name == "*":
                continue
            self.f.from_names[a.asname or a.name] = f"{mod}:{a.name}"
            # `from pkg import submodule` imports a module too
            self.f.imports.append(f"{mod}.{a.name}" if mod else a.name)

    # -- calls ---------------------------------------------------------
    def visit_Call(self, node):
        fn = node.func
        name, receiver = None, ""
        if isinstance(fn, ast.Name):
            name = fn.id
        elif isinstance(fn, ast.Attribute):
            name = fn.attr
            if isinstance(fn.value, ast.Name):
                receiver = fn.value.id
        if name:
            self.f.calls.append(Call(self._enclosing_def(), name, node.lineno, receiver))
        self.generic_visit(node)


def parse_file(abs_path: str, rel_path: str) -> FileFacts:
    facts = FileFacts(path=rel_path, module=path_to_module(rel_path))
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        tree = ast.parse(src, filename=rel_path)
    except (SyntaxError, ValueError, OSError) as e:
        facts.error = f"{type(e).__name__}: {e}"
        return facts
    _Visitor(facts).visit(tree)
    return facts


def _excluded(rel: str, patterns) -> bool:
    return any(fnmatch.fnmatch(rel, p) or rel == p.rstrip("/") or rel.startswith(p.rstrip("/") + "/")
               for p in patterns or ())


def iter_python_files(root: str, exclude=()):
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        rel_dir = "" if rel_dir == "." else rel_dir + "/"
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".") and not d.endswith(".egg-info")
            and not _excluded(rel_dir + d, exclude)
        )
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                abs_p = os.path.join(dirpath, fn)
                rel = os.path.relpath(abs_p, root).replace(os.sep, "/")
                if not _excluded(rel, exclude):
                    yield abs_p, rel


def parse_repo(root: str, exclude=()) -> list[FileFacts]:
    return [parse_file(a, r) for a, r in iter_python_files(root, exclude)]
