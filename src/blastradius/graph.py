"""Build a function-level call graph plus a file-level import graph.

Nodes are keyed by fqn: ``path/to/file.py::Class.method`` (definitions) or
``path/to/file.py`` (the file / module-level code).

Edges are ``{caller, callee, type, file, line}`` where ``type`` is ``calls``
or ``imports``. Call resolution is static and name based:

1. ``self.x()`` / ``cls.x()``  -> a method ``x`` on the enclosing class
2. a name bound by ``from mod import x`` -> ``x`` defined in ``mod``
3. ``alias.x()`` where ``alias`` is an imported module -> ``x`` in that module
4. a definition with that name in the same file
5. a single definition with that name anywhere in the repo
6. among several, the one whose file the caller imports

Anything else (stdlib, third party, truly ambiguous) is dropped rather than
guessed, so the graph under-reports instead of inventing edges.
"""

from __future__ import annotations

from collections import defaultdict

from .parser import FileFacts, parse_repo


def build_graph(root_or_facts, exclude=()) -> dict:
    facts: list[FileFacts] = (
        parse_repo(root_or_facts, exclude) if isinstance(root_or_facts, str) else list(root_or_facts)
    )
    nodes: dict[str, dict] = {}
    name_index: dict[str, list[str]] = defaultdict(list)
    module_to_file: dict[str, str] = {}
    errors: dict[str, str] = {}

    for f in facts:
        module_to_file[f.module] = f.path
        nodes[f.path] = {"file": f.path, "name": f.module or f.path, "kind": "file", "line": 0}
        if f.error:
            errors[f.path] = f.error
        for d in f.definitions:
            fqn = f"{f.path}::{d.qualname}"
            nodes[fqn] = {"file": f.path, "name": d.qualname, "kind": d.kind, "line": d.line}
            name_index[d.qualname.rsplit(".", 1)[-1]].append(fqn)

    def file_for_module(mod: str) -> str | None:
        # exact module, else the longest importable prefix (`a.b.c` -> `a.b`)
        parts = mod.split(".")
        while parts:
            hit = module_to_file.get(".".join(parts))
            if hit:
                return hit
            parts.pop()
        return None

    edges: list[dict] = []
    seen: set[tuple] = set()

    def add(caller, callee, typ, file, line):
        key = (caller, callee, typ)
        if key in seen or caller == callee:
            return
        seen.add(key)
        edges.append({"caller": caller, "callee": callee, "type": typ, "file": file, "line": line})

    for f in facts:
        imported_files = {p for p in (file_for_module(m) for m in f.imports) if p}
        for m in f.imports:
            target = file_for_module(m)
            if target and target != f.path:
                add(f.path, target, "imports", f.path, 0)

        for c in f.calls:
            caller = f"{f.path}::{c.caller}" if c.caller else f.path
            cands = name_index.get(c.name, [])
            if not cands:
                continue
            resolved = None
            # 1) self.method() -> method on the enclosing class
            if c.receiver in ("self", "cls") and c.caller:
                cls = c.caller.split(".")[0]
                want = f"{f.path}::{cls}.{c.name}"
                if want in nodes:
                    resolved = want
            # 2) from mod import name
            if resolved is None and not c.receiver and c.name in f.from_names:
                mod, _, orig = f.from_names[c.name].partition(":")
                tf = file_for_module(mod)
                if tf and f"{tf}::{orig}" in nodes:
                    resolved = f"{tf}::{orig}"
            # 3) alias.func() where alias is an imported module
            if resolved is None and c.receiver and c.receiver in f.from_names:
                mod, _, orig = f.from_names[c.receiver].partition(":")
                tf = file_for_module(f"{mod}.{orig}" if orig else mod)
                if tf and f"{tf}::{c.name}" in nodes:
                    resolved = f"{tf}::{c.name}"
            if resolved is None:
                same = [x for x in cands if x.startswith(f.path + "::")]
                plain = [x for x in same if "." not in x.split("::", 1)[1]]
                if not c.receiver and plain:
                    resolved = plain[0]
                elif len(cands) == 1:
                    resolved = cands[0]
                elif same and c.receiver in ("self", "cls"):
                    resolved = same[0]
                else:
                    via = [x for x in cands if x.split("::", 1)[0] in imported_files]
                    if len(via) == 1:
                        resolved = via[0]
            if resolved:
                add(caller, resolved, "calls", f.path, c.line)

    return {
        "root": root_or_facts if isinstance(root_or_facts, str) else "",
        "nodes": nodes,
        "edges": edges,
        "index": dict(name_index),
        "errors": errors,
    }
