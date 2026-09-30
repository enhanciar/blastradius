"""Command-line entry point: ``blastradius <repo_path> <function_or_file>``."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from . import __version__
from .graph import build_graph
from .impact import compute_impact

LIMIT = 40


def _render(r: dict, graph: dict, elapsed: float, show_all: bool) -> str:
    out = []
    n_funcs = sum(1 for v in graph["nodes"].values() if v["kind"] != "file")
    n_files = len(graph["nodes"]) - n_funcs
    out.append(f"blastradius: {n_files} files, {n_funcs} definitions, "
               f"{len(graph['edges'])} edges ({elapsed:.2f}s)")
    if not r["found"]:
        out.append(f"\nNot found: {r.get('error', r['target'])}")
        if r.get("suggestions"):
            out.append("Did you mean: " + ", ".join(r["suggestions"]))
        return "\n".join(out)

    res = r["resolved"]
    head = res[0]
    what = head["fqn"] + (f" (+{len(res) - 1} definitions in it)" if len(res) > 1 and r["matched_by"] == "file"
                          else f" (+{len(res) - 1} more with that name)" if len(res) > 1 else "")
    out.append(f"\nTarget: {what}")
    if r["matched_by"] != "file":
        for d in res:
            out.append(f"  defined at {d['file']}:{d['line']}")

    def cap(items):
        return items if show_all else items[:LIMIT]

    def more(items):
        return [f"  ... +{len(items) - LIMIT} more (use --all)"] if not show_all and len(items) > LIMIT else []

    dc = r["direct_callers"]
    calls = [d for d in dc if d["via"] == "calls"]
    imps = [d for d in dc if d["via"] == "imports"]
    out.append(f"\nDirect callers ({len(calls)})")
    for d in cap(calls):
        tag = "  [test]" if d["is_test"] else ""
        out.append(f"  {d['site']:<40} {d['fqn'].split('::')[-1] if '::' in d['fqn'] else '<module>'}"
                   f"  -> {d['calls'].split('::')[-1]}{tag}")
    out += more(calls)
    if imps:
        out.append(f"\nImported by ({len(imps)})")
        for d in cap(imps):
            out.append(f"  {d['file']}{'  [test]' if d['is_test'] else ''}")
        out += more(imps)

    td = r["transitive_dependents"]
    out.append(f"\nTransitive dependents ({len(td)}, up to {r['depth']} hops)")
    for d in cap(td):
        via = " <- ".join(p.split("::")[-1] for p in d["path"][1:3])
        tag = "  [test]" if d["is_test"] else ""
        out.append(f"  hop {d['hops']}  {d['file']}:{d['line']:<5} {d['fqn'].split('::')[-1] if '::' in d['fqn'] else '<module>'}"
                   f"  (via {via}){tag}")
    out += more(td)

    at = r["affected_tests"]
    out.append(f"\nAffected tests ({len(at)})")
    for d in cap(at):
        out.append(f"  {d['file']}:{d['line']}  {d['fqn'].split('::')[-1] if '::' in d['fqn'] else '<module>'}")
    out += more(at)
    if not at:
        out.append("  none found: no test reaches this target within the depth limit")

    af = r["affected_files"]
    nontest = [f for f in af if not any(t["file"] == f for t in at)]
    out.append(f"\nSummary: {len(dc)} direct, {len(td)} transitive, "
               f"{len(af)} other files ({len(nontest)} non-test), {len(at)} tests")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="blastradius",
        description="Show what could break if you change a Python function or file. "
                    "Local static analysis: no network, no AI key.")
    p.add_argument("repo", help="path to the repository root")
    p.add_argument("target", help="function (name, Class.method, or path.py::name) or file (path.py)")
    p.add_argument("-d", "--depth", type=int, default=3, help="max hops for transitive dependents (default 3)")
    p.add_argument("--json", action="store_true", help="print machine-readable JSON")
    p.add_argument("-x", "--exclude", action="append", default=[], metavar="PATH_OR_GLOB",
                   help="skip a directory or glob, relative to the repo (repeatable)")
    p.add_argument("--all", action="store_true", help="don't truncate long lists")
    p.add_argument("--version", action="version", version=f"blastradius {__version__}")
    a = p.parse_args(argv)

    if not os.path.isdir(a.repo):
        print(f"blastradius: not a directory: {a.repo}", file=sys.stderr)
        return 2
    t0 = time.perf_counter()
    graph = build_graph(os.path.abspath(a.repo), a.exclude)
    r = compute_impact(graph, a.target, a.depth)
    elapsed = time.perf_counter() - t0
    if a.json:
        r = {**r, "stats": {"files": sum(1 for v in graph["nodes"].values() if v["kind"] == "file"),
                            "nodes": len(graph["nodes"]), "edges": len(graph["edges"]),
                            "parse_errors": graph["errors"], "seconds": round(elapsed, 3)}}
        print(json.dumps(r, indent=2))
    else:
        print(_render(r, graph, elapsed, a.all))
    return 0 if r["found"] else 1


if __name__ == "__main__":
    sys.exit(main())
