"""Blast-radius engine: given a function or file, who depends on it?

:func:`compute_impact` never raises. If the target can't be resolved it
returns ``found: False`` with a reason and close-match suggestions.
"""

from __future__ import annotations

import difflib
import os
import re
from collections import deque

_TEST_FILE = re.compile(r"(^test_.*\.py$|_test\.py$|^conftest\.py$)")
_TEST_DIR = re.compile(r"(^|/)(tests?|testing)(/)")


def is_test_file(path: str) -> bool:
    return bool(_TEST_FILE.search(os.path.basename(path or "")) or _TEST_DIR.search(path or ""))


def _file_of(fqn: str) -> str:
    return fqn.split("::", 1)[0]


def resolve_target(graph: dict, target: str) -> tuple[list[str], str]:
    """Map user input to node fqns. Returns (fqns, how_it_matched)."""
    nodes, index = graph["nodes"], graph["index"]
    t = target.strip().replace("\\", "/")
    if t.startswith("./"):
        t = t[2:]
    root = graph.get("root") or ""
    if root and os.path.isabs(t):
        rel = os.path.relpath(t, root).replace(os.sep, "/")
        if not rel.startswith(".."):
            t = rel
    if t in nodes:
        # a file: seed with the file node and every definition inside it
        if nodes[t]["kind"] == "file":
            return [t] + [k for k in nodes if k.startswith(t + "::")], "file"
        return [t], "exact"
    if "::" in t:
        path, _, name = t.partition("::")
        hits = [k for k in nodes if "::" in k and k.split("::", 1)[1] == name
                and (k.endswith("/" + path + "::" + name) or _file_of(k).endswith(path))]
        if hits:
            return hits, "qualified"
        return [], "unresolved"
    # file path suffix, e.g. "billing.py" or "shop/billing.py"
    if t.endswith(".py"):
        files = [k for k, v in nodes.items() if v["kind"] == "file"
                 and (k == t or k.endswith("/" + t))]
        if len(files) >= 1:
            out = []
            for fp in files:
                out += [fp] + [k for k in nodes if k.startswith(fp + "::")]
            return out, "file"
    # "Class.method" or bare name
    hits = [k for k in nodes if "::" in k and k.split("::", 1)[1] == t]
    if hits:
        return hits, "name"
    if t in index:
        return list(index[t]), "name"
    return [], "unresolved"


def _suggest(graph: dict, target: str) -> list[str]:
    names = set(graph["index"]) | {k for k, v in graph["nodes"].items() if v["kind"] == "file"}
    base = target.split("::")[-1]
    return difflib.get_close_matches(base, sorted(names), n=5, cutoff=0.6)


def _loc(graph: dict, fqn: str) -> dict:
    n = graph["nodes"].get(fqn, {})
    return {"fqn": fqn, "file": n.get("file", _file_of(fqn)), "line": n.get("line", 0),
            "kind": n.get("kind", "?"), "is_test": is_test_file(n.get("file", _file_of(fqn)))}


def compute_impact(graph: dict, target: str, depth: int = 3) -> dict:
    try:
        depth = max(1, int(depth))
    except (TypeError, ValueError):
        depth = 3
    base = {"target": target, "found": False, "resolved": [], "direct_callers": [],
            "transitive_dependents": [], "affected_files": [], "affected_tests": [],
            "depends_on": [], "depth": depth}
    try:
        if not (target or "").strip():
            return {**base, "error": "empty target"}
        seeds, how = resolve_target(graph, target)
        if not seeds:
            return {**base, "error": f"'{target}' not found in the graph",
                    "suggestions": _suggest(graph, target)}
        seed_set = set(seeds)

        rev: dict[str, list[dict]] = {}
        fwd: dict[str, list[dict]] = {}
        for e in graph["edges"]:
            rev.setdefault(e["callee"], []).append(e)
            fwd.setdefault(e["caller"], []).append(e)

        # direct callers: one hop, with the exact call site file:line
        direct: dict[tuple, dict] = {}
        for s in seeds:
            for e in rev.get(s, []):
                if e["caller"] in seed_set:
                    continue
                key = (e["caller"], e["callee"], e["type"])
                direct[key] = {**_loc(graph, e["caller"]), "calls": e["callee"],
                               "via": e["type"], "site": f"{e['file']}:{e['line']}" if e["line"] else e["file"]}

        # transitive dependents: BFS over reverse edges, hops 2..depth
        hop: dict[str, int] = {s: 0 for s in seeds}
        parent: dict[str, str] = {}
        q = deque(seeds)
        while q:
            cur = q.popleft()
            if hop[cur] >= depth:
                continue
            for e in rev.get(cur, []):
                nxt = e["caller"]
                if nxt in hop:
                    continue
                hop[nxt] = hop[cur] + 1
                parent[nxt] = cur
                q.append(nxt)

        def chain(n):
            out = [n]
            while out[-1] in parent:
                out.append(parent[out[-1]])
            return out

        transitive = [
            {**_loc(graph, n), "hops": h, "path": chain(n)}
            for n, h in hop.items() if h >= 2
        ]
        transitive.sort(key=lambda d: (d["hops"], d["file"], d["line"]))

        dependents = [n for n, h in hop.items() if h >= 1]
        affected_files = sorted({_file_of(n) for n in dependents} - {_file_of(s) for s in seeds})
        tests = sorted({n for n in dependents if is_test_file(_file_of(n))})
        affected_tests = [_loc(graph, n) for n in tests]

        depends_on = sorted({e["callee"] for s in seeds for e in fwd.get(s, [])
                             if e["type"] == "calls" and e["callee"] not in seed_set})

        return {
            **base,
            "found": True,
            "matched_by": how,
            "resolved": [_loc(graph, s) for s in seeds],
            "direct_callers": sorted(direct.values(), key=lambda d: (d["via"], d["file"], d["line"])),
            "transitive_dependents": transitive,
            "affected_files": affected_files,
            "affected_tests": affected_tests,
            "depends_on": [_loc(graph, n) for n in depends_on],
        }
    except Exception as e:  # noqa: BLE001 - contract: never raise
        return {**base, "error": f"{type(e).__name__}: {e}"}
