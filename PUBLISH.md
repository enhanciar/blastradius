# Publishing blastradius

Nothing has been published yet. Publishing needs your GitHub and PyPI accounts.

## 0. Pre-flight

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[test]' build twine
pytest                                   # expect all green
blastradius /path/to/some/repo some_function   # sanity run
grep -rnEi "https?://|/Users/|api[_-]?key|secret|password" src/ tests/   # expect only enhanciar.in / test words
```

PyPI name: `blastradius` and `blastradius-cli` were both taken on PyPI when checked on 2026-09-30, so the
distribution is named **`blastradius-py`** in `pyproject.toml`. It was free then. The installed
command and the import name are still `blastradius`. Re-check before uploading.

## 1. GitHub

1. Create an empty public repo, e.g. `github.com/<org>/blastradius`. Don't add a README or license there, since both are already in this repo.
2. Push:
   ```bash
   git remote add origin git@github.com:<org>/blastradius.git
   git push -u origin main
   ```
3. Replace `<you>` in the README's `pip install git+https://github.com/<you>/blastradius` line.
4. Add a `Repository` URL under `[project.urls]` in `pyproject.toml`.
5. Repo settings: add the description "See what breaks before you change a function" and the topics
   `python`, `static-analysis`, `call-graph`, `refactoring`, `cli`.
6. Optional: add a GitHub Action that runs `pytest` on 3.10 to 3.13.

## 2. PyPI

```bash
rm -rf dist && python -m build
twine check dist/*
twine upload --repository testpypi dist/*    # dry run on test.pypi.org first
pip install -i https://test.pypi.org/simple/ blastradius-py && blastradius --version
twine upload dist/*                          # real upload (uses your PyPI API token)
```

For later releases, bump `version` in `pyproject.toml` and `__version__` in
`src/blastradius/__init__.py` together, then `git tag v0.x.y && git push --tags`.

## 3. Show HN

Post Tuesday to Thursday, around 8 to 10am ET. Stay in the thread for 3+ hours. Don't ask for upvotes.
Link to the GitHub repo, not enhanciar.in.

**Title**
> Show HN: Blastradius – see what breaks before you change a function

(Alt: "Show HN: A local CLI that tells you what breaks if you change this code")

**First comment.** This is the growth-kit draft, edited to match what v0.1 actually does.
The draft promised cross-repo edges, JS/TS and an MCP mode. v0.1 has none of these, so they are
removed below. Add them back only if you ship them.

> Hi HN, solo founder from India here. This is the blast-radius engine from my product (Enhanciar), pulled out as a standalone MIT CLI.
>
> You give it a Python repo and a function or file (`path.py::func`, `Class.method`, or `billing.py`). It parses the repo with the stdlib `ast` module, builds a call and import graph, and walks callers N hops out. It prints the direct callers with the exact file:line of each call, the transitive dependents with the chain that reaches them, and which of those are tests. `--json` is there for CI or agents. If it can't find the target, it says why and suggests close matches.
>
> Why I built it: I kept changing "small" helpers, tests passed, and something far away broke. grep tells you where a name appears, not what depends on it.
>
> Limits, honestly: it's static analysis, so it misses dynamic dispatch, getattr, callbacks and inheritance. It's Python only for now. When a call is ambiguous, it drops the edge rather than guessing, so it under-reports instead of inventing callers.
>
> It runs fully locally, with no dependencies, no AI and no key. On a ~400-file repo it takes about a second.
>
> The hosted product adds the "why": links to the Slack threads and tickets behind the code. But the CLI is useful by itself. I'd love feedback on the graph quality, and on repos where it gets things wrong.
