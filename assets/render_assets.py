"""Render blastradius promo assets (enhanciar.in site theme) with Playwright + ffmpeg.

usage: /usr/bin/python3 assets/render_assets.py
Terminal text is the REAL CLI output, captured at render time from tests/fixtures/shop.
"""
import html, os, pathlib, shutil, subprocess, tempfile
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
CMD = "blastradius . shop/money.py::apply_tax"
LOGO = (ROOT.parent.parent / "frontend/public/favicon.svg")
LOGO_SVG = LOGO.read_text() if LOGO.exists() else ""

out = subprocess.run(["python3", "-m", "blastradius", ".", "shop/money.py::apply_tax"],
                     cwd=ROOT / "tests/fixtures/shop", env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                     capture_output=True, text=True, check=True).stdout
LINES = out.rstrip("\n").split("\n")


def color(line):
    e = html.escape(line)
    if line.startswith("Direct callers"): return f'<span class="tc b">{e}</span>'
    if line.startswith("Transitive dependents"): return f'<span class="sg b">{e}</span>'
    if line.startswith("Affected tests"): return f'<span class="sb b">{e}</span>'
    if line.startswith("Target:"): return f'<span class="b w">{e}</span>'
    if line.startswith("blastradius:") or line.startswith("Summary"): return f'<span class="dim">{e}</span>'
    if "[test]" in line: return e.replace("[test]", '<span class="tag">[test]</span>')
    return e


FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Inclusive+Sans:wght@400;600&family=JetBrains+Mono:wght@400;500;700&display=block" rel="stylesheet">')

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#FBFAF4;--s2:#F2F1EB;--ink:#0E1113;--teal:#1C525D;--rose:#B6969D;--sage:#ADB49C;--terra:#DB704C;--sb:#C3D3CE;
--H:"Inclusive Sans",sans-serif;--M:"JetBrains Mono",monospace}
body{background:var(--bg);color:var(--ink);font-family:var(--M);overflow:hidden;position:relative}
.eye{font:500 13px var(--M);letter-spacing:2.2px;text-transform:uppercase;color:rgba(14,17,19,.62)}
.h{font-family:var(--H);font-weight:600;letter-spacing:-.025em;line-height:1.02;color:var(--ink)}
.chip{display:inline-block;background:var(--s2);border-radius:999px;padding:9px 18px;font:500 15px var(--M);color:var(--ink)}
.pill{display:inline-block;background:var(--ink);color:var(--bg);border-radius:999px;padding:12px 24px;font:500 16px var(--M)}
.opill{display:inline-block;border:1.5px solid var(--ink);border-radius:999px;padding:10px 22px;font:500 15px var(--M)}
.term{background:var(--ink);border-radius:22px;overflow:hidden;box-shadow:0 18px 40px rgba(14,17,19,.12)}
.term.teal{background:var(--teal)}
.bar{height:38px;display:flex;align-items:center;gap:8px;padding:0 18px;position:relative;border-bottom:1px solid rgba(251,250,244,.1)}
.bar i{width:11px;height:11px;border-radius:50%;display:block;background:rgba(251,250,244,.25)}
.bar span{position:absolute;left:0;right:0;text-align:center;font:500 12px var(--M);color:rgba(251,250,244,.5)}
pre{font-family:var(--M);color:rgba(251,250,244,.86);white-space:pre;padding:18px 22px}
.b{font-weight:700}.w{color:var(--bg)}.tc{color:var(--terra)}.sg{color:var(--sage)}.sb{color:var(--sb)}.dim{color:rgba(251,250,244,.45)}
.tag{color:var(--ink);background:var(--rose);border-radius:4px;padding:0 5px;font-weight:700}
.ps{color:var(--sage)}.cur{display:inline-block;width:.6em;background:var(--bg);height:1.1em;vertical-align:-.15em}
.brand{display:flex;align-items:center;gap:10px;font:500 15px var(--M);color:var(--ink)}
.brand svg{width:28px;height:28px;border-radius:7px}
"""


def term(body, size, title="zsh — shop", cls=""):
    return (f'<div class="term {cls}"><div class="bar"><i></i><i></i><i></i><span>{title}</span></div>'
            f'<pre style="font-size:{size}px;line-height:1.55">{body}</pre></div>')


def snippet(keep):
    return "\n".join([f'<span class="ps">$</span> <span class="w">{html.escape(CMD)}</span>'] +
                      [color(LINES[i]) for i in keep])


def page(w, h, inner):
    return f"<!doctype html><html><head><meta charset=utf-8>{FONTS}<style>{CSS}body{{width:{w}px;height:{h}px}}</style></head><body>{inner}</body></html>"


BRAND = f'<div class="brand">{LOGO_SVG}<span>by Enhanciar</span></div>'


def stills(pg):
    # 1. GitHub social preview 1280x640, ~80px safe margin
    idx = [i for i, l in enumerate(LINES) if l.startswith(("Direct", "  shop/billing.py:12", "Affected", "  tests/test_billing.py:4  "))]
    inner = f"""
    <div style="position:absolute;left:80px;top:80px;width:540px">
      <div class="eye">Blastradius · Free &amp; open source</div>
      <div class="h" style="font-size:60px;margin-top:22px">See what breaks before you change a function.</div>
    </div>
    <div style="position:absolute;right:84px;top:150px;display:inline-block;transform:rotate(2.5deg)">{term(snippet(idx), 10.5)}</div>
    <div style="position:absolute;left:80px;right:80px;bottom:80px;display:flex;justify-content:space-between;align-items:center">
      <div class="chip">pip install git+https://github.com/enhanciar/blastradius</div>{BRAND}</div>"""
    shot(pg, 1280, 640, inner, "social-preview.png")

    # 2. square post 1080x1080
    keep = [i for i, l in enumerate(LINES) if l and not l.startswith(("blastradius:", "Summary", "  defined"))]
    inner = f"""
    <div style="position:absolute;left:80px;right:80px;top:80px">
      <div class="eye">Blastradius · Impact tracing for Python</div>
      <div class="h" style="font-size:64px;margin-top:20px">Changed one small function. Something far away broke.</div>
    </div>
    <div style="position:absolute;left:80px;right:80px;top:420px;transform:rotate(-1.2deg)">{term(snippet(keep), 15.5)}</div>
    <div style="position:absolute;left:80px;right:80px;bottom:80px;display:flex;justify-content:space-between;align-items:center">
      <div style="display:flex;gap:14px;align-items:center"><span class="pill">Free &amp; open source</span>
      <span class="opill">github.com/enhanciar/blastradius</span></div>{BRAND}</div>"""
    shot(pg, 1080, 1080, inner, "post-square.png")

    # 3. dev.to cover 1000x420
    cards = "".join(f'<div style="position:absolute;width:150px;height:190px;border-radius:20px;background:{c};{p}"></div>' for c, p in [
        ("#ADB49C", "right:150px;top:70px;transform:rotate(-8deg)"), ("#DB704C", "right:95px;top:110px;transform:rotate(4deg)"),
        ("#1C525D", "right:40px;top:150px;transform:rotate(-3deg)")])
    inner = cards + f"""
    <div style="position:absolute;left:64px;top:60px;width:600px">
      <div class="eye">Blastradius · Impact tracing · Python</div>
      <div class="h" style="font-size:46px;margin-top:18px">How I find what breaks before I change a Python function</div>
    </div>
    <div style="position:absolute;left:64px;bottom:56px">{BRAND}</div>"""
    shot(pg, 1000, 420, inner, "devto-cover.png")


def load(pg, w, h, inner):
    pg.set_viewport_size({"width": w, "height": h})
    pg.set_content(page(w, h, inner), wait_until="networkidle")
    pg.evaluate("document.fonts.ready")
    ok = pg.evaluate("[document.fonts.check('600 40px \"Inclusive Sans\"'), document.fonts.check('500 14px \"JetBrains Mono\"')]")
    assert all(ok), f"fonts not loaded: {ok}"


def shot(pg, w, h, inner, name):
    load(pg, w, h, inner)
    pg.screenshot(path=str(HERE / name))


def demo(pg, tmp):
    W, H, FPS = 900, 640, 12
    pg.set_viewport_size({"width": W, "height": H})
    body = [color(l) for l in LINES]
    inner = f"""<div style="position:absolute;left:44px;right:44px;top:34px">
      <div class="eye">Blastradius · Free &amp; open source</div>
      <div class="h" style="font-size:38px;margin-top:10px">See what breaks before you change it.</div></div>
    <div style="position:absolute;left:44px;right:44px;top:132px">{term("<span id=t></span>", 12.5)}</div>"""
    load(pg, W, H, inner)
    pg.evaluate("""([cmd, body]) => { window.R = (t) => {
      const n = Math.max(0, Math.min(cmd.length, Math.floor((t-0.5)/0.055)));
      const cur = (Math.floor(t*2.5)%2===0) ? '<span class="cur"></span>' : '';
      let s = '<span class="ps">~/shop $</span> <span class="w">' + cmd.slice(0,n) + '</span>';
      if (t < 2.9) { document.getElementById('t').innerHTML = s + cur; return; }
      const k = Math.min(body.length, Math.floor((t-3.0)/0.14)+1);
      s += '\\n' + body.slice(0, Math.max(0,k)).join('\\n');
      if (k >= body.length) s += '\\n\\n<span class="ps">~/shop $</span> ' + cur;
      document.getElementById('t').innerHTML = s; } }""", [CMD, body])
    N = int(10.5 * FPS)
    for f in range(N):
        pg.evaluate(f"R({f / FPS})")
        pg.screenshot(path=f"{tmp}/f{f:04d}.png")
    pal = f"{tmp}/pal.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/f%04d.png",
                    "-vf", "palettegen=max_colors=128:stats_mode=full:reserve_transparent=0", pal], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/f%04d.png", "-i", pal,
                    "-lavfi", "paletteuse=dither=none:diff_mode=rectangle", "-loop", "0", str(HERE / "demo.gif")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/f%04d.png",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart", str(HERE / "demo.mp4")], check=True)


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page()
        stills(pg)
        demo(pg, tmp)
        b.close()
    shutil.rmtree(tmp)
    for f in sorted(HERE.iterdir()):
        print(f.name, f.stat().st_size)
