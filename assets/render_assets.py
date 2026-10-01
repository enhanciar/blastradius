"""Render blastradius promo assets (Enhanciar showreel style) with Playwright + ffmpeg.

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
    if line.startswith("Direct callers"): return f'<span class="vi b">{e}</span>'
    if line.startswith("Transitive dependents"): return f'<span class="bl b">{e}</span>'
    if line.startswith("Affected tests"): return f'<span class="mi b">{e}</span>'
    if line.startswith("Target:"): return f'<span class="b w">{e}</span>'
    if line.startswith("blastradius:") or line.startswith("Summary"): return f'<span class="dim">{e}</span>'
    if "[test]" in line: return e.replace("[test]", '<span class="tag">[test]</span>')
    return e


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{--navy:#0e0b2b;--blue:#2563eb;--vio:#6f4cff;--mint:#a8f0c6;--F:"Helvetica Neue",Helvetica,Arial,sans-serif;--M:"SF Mono",Menlo,monospace}
body{background:var(--navy);color:#fff;font-family:var(--F);overflow:hidden;position:relative}
.hud{position:absolute;width:26px;height:26px;border-color:rgba(255,255,255,.45);border-style:solid;border-width:0}
.tl{border-top-width:1.5px;border-left-width:1.5px}.tr{border-top-width:1.5px;border-right-width:1.5px}
.bl_{border-bottom-width:1.5px;border-left-width:1.5px}.br{border-bottom-width:1.5px;border-right-width:1.5px}
.lab{position:absolute;font:600 12px var(--M);letter-spacing:2.5px;color:rgba(255,255,255,.55);text-transform:uppercase}
.term{background:#07061a;border:1px solid rgba(255,255,255,.12);border-radius:12px;overflow:hidden;box-shadow:0 30px 60px rgba(0,0,0,.4)}
.bar{height:34px;display:flex;align-items:center;gap:8px;padding:0 14px;background:#141233;position:relative}
.bar i{width:12px;height:12px;border-radius:50%;display:block}
.bar span{position:absolute;left:0;right:0;text-align:center;font:500 12px var(--M);color:rgba(255,255,255,.45)}
pre{font-family:var(--M);color:#d6d8ee;white-space:pre;padding:16px 20px}
.b{font-weight:700}.w{color:#fff}.vi{color:#b9a6ff}.bl{color:#7fb0ff}.mi{color:var(--mint)}.dim{color:#7b7fa3}
.tag{color:#0e0b2b;background:var(--mint);border-radius:3px;padding:0 4px;font-weight:700}
.ps{color:var(--mint)}.cur{display:inline-block;width:.6em;background:#fff;height:1.1em;vertical-align:-.15em}
.brand{display:flex;align-items:center;gap:10px;font:600 15px var(--M);letter-spacing:2px;color:rgba(255,255,255,.8)}
.brand svg{width:26px;height:26px;border-radius:6px}
"""


def hud(pad, labels):
    s = "".join(f'<div class="hud {c}" style="{p}"></div>' for c, p in [
        ("tl", f"top:{pad}px;left:{pad}px"), ("tr", f"top:{pad}px;right:{pad}px"),
        ("bl_", f"bottom:{pad}px;left:{pad}px"), ("br", f"bottom:{pad}px;right:{pad}px")])
    pos = [f"top:{pad+8}px;left:{pad+36}px", f"top:{pad+8}px;right:{pad+36}px",
           f"bottom:{pad+8}px;left:{pad+36}px", f"bottom:{pad+8}px;right:{pad+36}px"]
    return s + "".join(f'<div class="lab" style="{p}">{html.escape(t)}</div>' for p, t in zip(pos, labels) if t)


def term(body, size, title="zsh — shop"):
    return (f'<div class="term"><div class="bar"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i>'
            f'<i style="background:#28c840"></i><span>{title}</span></div><pre style="font-size:{size}px;line-height:1.5">{body}</pre></div>')


def snippet(keep):
    return "\n".join([f'<span class="ps">$</span> <span class="w">{html.escape(CMD)}</span>'] +
                     [color(LINES[i]) for i in keep])


def page(w, h, inner):
    return f"<!doctype html><html><head><meta charset=utf-8><style>{CSS}body{{width:{w}px;height:{h}px}}</style></head><body>{inner}</body></html>"


BRAND = f'<div class="brand">{LOGO_SVG}<span>BY ENHANCIAR</span></div>'


def stills(pg):
    # 1. GitHub social preview 1280x640 (content inside ~80px safe margin)
    idx = [i for i, l in enumerate(LINES) if l.startswith(("Direct", "  shop/billing.py:12", "Affected", "  tests/test_billing.py:4  "))]
    inner = hud(28, ["BLASTRADIUS · v0.1", "FIG. 01", "PYTHON CLI", "LOCAL · OFFLINE"]) + f"""
    <div style="position:absolute;left:90px;top:96px;width:640px">
      <div style="font:700 30px var(--M);color:var(--mint);letter-spacing:1px">blastradius</div>
      <div style="font:900 74px/0.98 var(--F);letter-spacing:-2px;margin-top:22px">SEE WHAT BREAKS<br><span style="color:#8f78ff">BEFORE YOU<br>CHANGE IT.</span></div>
    </div>
    <div style="position:absolute;right:80px;top:120px;width:530px">{term(snippet(idx), 11.5)}</div>
    <div style="position:absolute;left:90px;right:90px;bottom:84px;display:flex;justify-content:space-between;align-items:center">
      <div style="font:600 15px var(--M);color:rgba(255,255,255,.8)">free · MIT · no AI key · <span style="color:var(--mint)">pip install git+https://github.com/enhanciar/blastradius</span></div>
      {BRAND}</div>"""
    shot(pg, 1280, 640, inner, "social-preview.png")

    # 2. square post 1080x1080
    keep = [i for i, l in enumerate(LINES) if l and not l.startswith(("blastradius:", "Summary", "  defined"))]
    inner = f"""<div style="position:absolute;top:0;left:0;right:0;height:430px;background:var(--blue)"></div>""" + \
        hud(30, ["BLASTRADIUS", "FIG. 02", "FREE & OPEN SOURCE", "MIT"]) + f"""
    <div style="position:absolute;left:80px;right:80px;top:96px">
      <div style="font:700 16px var(--M);letter-spacing:4px;color:rgba(255,255,255,.75)">MONDAY · 9:02</div>
      <div style="font:900 66px/1.0 var(--F);letter-spacing:-2px;margin-top:20px">CHANGED ONE<br>SMALL FUNCTION.</div>
      <div style="font:900 66px/1.0 var(--F);letter-spacing:-2px;color:var(--navy);margin-top:6px">SOMETHING FAR<br>AWAY BROKE.</div>
    </div>
    <div style="position:absolute;left:80px;right:80px;top:470px">{term(snippet(keep), 15.5)}</div>
    <div style="position:absolute;left:80px;right:80px;bottom:84px;display:flex;justify-content:space-between;align-items:flex-end">
      <div><div style="font:900 40px var(--F);color:var(--mint);letter-spacing:-1px">FREE &amp; OPEN SOURCE</div>
      <div style="font:600 22px var(--M);margin-top:8px">github.com/enhanciar/blastradius</div></div>{BRAND}</div>"""
    shot(pg, 1080, 1080, inner, "post-square.png")

    # 3. dev.to cover 1000x420
    inner = f'<div style="position:absolute;right:0;top:0;bottom:0;width:250px;background:var(--vio)"></div>' + \
        hud(22, ["DEV NOTES", "FIG. 03", "blastradius", ""]) + f"""
    <div style="position:absolute;left:70px;top:70px;width:720px">
      <div style="font:700 15px var(--M);letter-spacing:4px;color:var(--mint)">BLASTRADIUS · PYTHON</div>
      <div style="font:900 50px/1.04 var(--F);letter-spacing:-1.5px;margin-top:16px">How I find what breaks<br>before I change a<br><span style="color:#8f78ff">Python function</span></div>
    </div>
    <div style="position:absolute;left:70px;bottom:62px">{BRAND}</div>
    <div style="position:absolute;right:62px;top:50%;transform:translateY(-50%);width:130px;height:130px;border-radius:50%;border:2px solid #fff;display:grid;place-items:center">
      <div style="width:70px;height:70px;border-radius:50%;border:2px solid var(--mint);display:grid;place-items:center"><div style="width:18px;height:18px;border-radius:50%;background:#fff"></div></div></div>"""
    shot(pg, 1000, 420, inner, "devto-cover.png")


def shot(pg, w, h, inner, name):
    pg.set_viewport_size({"width": w, "height": h})
    pg.set_content(page(w, h, inner))
    pg.screenshot(path=str(HERE / name))


def demo(pg, tmp):
    W, H, FPS = 900, 600, 12
    pg.set_viewport_size({"width": W, "height": H})
    body = [color(l) for l in LINES]
    inner = hud(16, ["BLASTRADIUS", "", "", "NO AI KEY · OFFLINE"]) + \
        f'<div style="position:absolute;left:36px;right:36px;top:46px">{term("<span id=t></span>", 13.5)}</div>'
    pg.set_content(page(W, H, inner))
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
