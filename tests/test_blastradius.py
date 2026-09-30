import json
import os

import pytest

from blastradius import build_graph, compute_impact
from blastradius.cli import main
from blastradius.impact import is_test_file

SHOP = os.path.join(os.path.dirname(__file__), "fixtures", "shop")


@pytest.fixture(scope="module")
def graph():
    return build_graph(SHOP)


def fqns(items):
    return {d["fqn"] for d in items}


def test_graph_nodes_and_parse_errors(graph):
    n = graph["nodes"]
    assert n["shop/billing.py::Invoice.total"]["kind"] == "method"
    assert n["shop/money.py::apply_tax"]["line"] == 5
    assert "broken.py" in graph["errors"]  # syntax error recorded, not raised


def test_edges_resolve_imports_and_self(graph):
    calls = {(e["caller"], e["callee"]) for e in graph["edges"] if e["type"] == "calls"}
    assert ("shop/billing.py::Invoice.total", "shop/money.py::apply_tax") in calls      # from-import
    assert ("shop/billing.py::Invoice.total", "shop/billing.py::Invoice.subtotal") in calls  # self.
    assert ("shop/api.py::checkout", "shop/billing.py::charge") in calls               # module alias
    assert ("shop/money.py::apply_tax", "shop/money.py::round_cents") in calls          # same file
    imps = {(e["caller"], e["callee"]) for e in graph["edges"] if e["type"] == "imports"}
    assert ("shop/api.py", "shop/billing.py") in imps
    assert ("shop/billing.py", "shop/money.py") in imps


def test_direct_callers_have_call_site(graph):
    r = compute_impact(graph, "apply_tax")
    assert r["found"]
    (d,) = [d for d in r["direct_callers"] if d["via"] == "calls"]
    assert d["fqn"] == "shop/billing.py::Invoice.total"
    assert d["site"] == "shop/billing.py:12"


def test_transitive_and_tests(graph):
    r = compute_impact(graph, "shop/money.py::apply_tax", depth=5)
    t = fqns(r["transitive_dependents"])
    assert "shop/billing.py::charge" in t
    assert "shop/api.py::checkout" in t
    assert fqns(r["affected_tests"]) == {"tests/test_billing.py::test_charge",
                                         "tests/test_api.py::test_checkout"}
    hops = {d["fqn"]: d["hops"] for d in r["transitive_dependents"]}
    assert hops["shop/billing.py::charge"] == 2


def test_depth_limits_walk(graph):
    r = compute_impact(graph, "apply_tax", depth=1)
    assert r["transitive_dependents"] == []
    assert r["affected_tests"] == []


def test_file_target_includes_importers(graph):
    r = compute_impact(graph, "shop/billing.py")
    assert r["matched_by"] == "file"
    assert "shop/api.py" in r["affected_files"]
    assert "tests/test_billing.py" in r["affected_files"]


def test_leaf_function_has_no_callers(graph):
    r = compute_impact(graph, "health")
    assert r["found"] and r["direct_callers"] == [] and r["transitive_dependents"] == []


def test_not_found_never_raises(graph):
    r = compute_impact(graph, "aply_tax")
    assert not r["found"] and "apply_tax" in r["suggestions"]
    assert compute_impact(graph, "")["found"] is False
    assert compute_impact({"nodes": None}, "x")["found"] is False  # garbage graph


def test_is_test_file():
    assert is_test_file("tests/foo.py")
    assert is_test_file("pkg/test_x.py")
    assert is_test_file("x_test.py")
    assert not is_test_file("shop/contest.py")
    assert not is_test_file("shop/billing.py")


def test_cli_json(capsys):
    assert main([SHOP, "apply_tax", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["found"] and data["stats"]["files"] >= 6


def test_cli_text_and_missing(capsys):
    assert main([SHOP, "Invoice.subtotal"]) == 0
    out = capsys.readouterr().out
    assert "Direct callers (1)" in out and "shop/billing.py:12" in out
    assert main([SHOP, "nope_nothing"]) == 1
    assert main([os.path.join(SHOP, "missing_dir"), "x"]) == 2


def test_exclude_skips_paths():
    g = build_graph(SHOP, exclude=["tests", "broken.py"])
    assert not any(k.startswith("tests/") for k in g["nodes"])
    assert "broken.py" not in g["nodes"]
    r = compute_impact(g, "apply_tax", depth=5)
    assert r["affected_tests"] == []
