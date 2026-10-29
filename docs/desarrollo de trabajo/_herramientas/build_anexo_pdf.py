#!/usr/bin/env python
"""
Compila anexos Markdown -> PDF A4 (Chromium/Playwright).

* Los bloques ```mermaid se renderizan a PNG con @mermaid-js/mermaid-cli (npx) y se
  incrustan como figuras; si un diagrama es invalido el script FALLA y muestra el error.
* Formulas: $...$ y $$...$$ con KaTeX (CDN). Si no hay red, se muestran como texto.
* Uso:  python build_anexo_pdf.py <archivo.md> [<archivo2.md> ...] [--out DIR]
        (por defecto el PDF se escribe en la carpeta padre de la carpeta 'fuentes').
"""
import hashlib, html, re, subprocess, sys, tempfile
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

CACHE = Path(tempfile.gettempdir()) / "mmd_cache"
CACHE.mkdir(exist_ok=True)
NPX = r"C:\Program Files\nodejs\npx.cmd"

CSS = """
@page { size: A4; margin: 22mm 18mm 22mm 18mm; }
body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 10.5pt; line-height: 1.5; color:#1b1f24; }
h1 { font-size: 21pt; color:#0b3d6b; border-bottom: 3px solid #0b3d6b; padding-bottom:6px; margin-top:0; }
h2 { font-size: 15pt; color:#0b3d6b; border-bottom: 1px solid #c8d3df; padding-bottom:3px; margin-top:26px; page-break-after: avoid; }
h3 { font-size: 12.5pt; color:#17497a; margin-top:18px; page-break-after: avoid; }
h4 { font-size: 11pt; color:#17497a; page-break-after: avoid; }
p { text-align: justify; margin: 6px 0; }
table { border-collapse: collapse; width:100%; margin: 10px 0 14px; font-size: 9.2pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th { background:#0b3d6b; color:#fff; padding:5px 7px; text-align:left; border:1px solid #0b3d6b; }
td { padding:4px 7px; border:1px solid #c8d3df; vertical-align: top; }
tbody tr:nth-child(even) td { background:#f3f7fb; }
code { font-family: Consolas, 'Courier New', monospace; font-size: 8.8pt; background:#eef2f6; padding:1px 3px; border-radius:3px; }
pre { background:#0f1b2a; color:#e8eef5; padding:10px 12px; border-radius:5px; font-size:8.4pt; line-height:1.35;
      white-space: pre-wrap; word-wrap: break-word; page-break-inside: avoid; }
pre code { background:transparent; color:inherit; padding:0; font-size:inherit; }
blockquote { border-left:4px solid #1e88e5; background:#eef5fc; margin:10px 0; padding:6px 12px; color:#243b53; }
figure { margin: 14px 0; text-align:center; page-break-inside: avoid; }
figure img { max-width: 100%; max-height: 215mm; }
figcaption { font-size: 9pt; color:#4a5a6a; font-style: italic; margin-top:4px; }
.meta { background:#f3f7fb; border:1px solid #c8d3df; border-radius:6px; padding:8px 12px; font-size:9.5pt; margin-bottom:14px; }
hr { border:0; border-top:1px solid #c8d3df; margin:18px 0; }
"""

HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
<style>{css}</style></head><body>{body}
<script>
window.addEventListener('load',function(){{ try{{ renderMathInElement(document.body,{{delimiters:[
 {{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}}],throwOnError:false}}); }}catch(e){{}} document.body.setAttribute('data-ready','1'); }});
</script></body></html>"""


def render_mermaid(code: str, src: Path) -> Path:
    h = hashlib.sha1(code.encode("utf-8")).hexdigest()[:16]
    png = CACHE / f"{h}.png"
    if png.exists():
        return png
    mmd = CACHE / f"{h}.mmd"
    mmd.write_text(code, encoding="utf-8")
    r = subprocess.run([NPX, "--yes", "@mermaid-js/mermaid-cli", "-i", str(mmd), "-o", str(png),
                        "-s", "3", "-b", "white"], capture_output=True, text=True, shell=False)
    if r.returncode != 0 or not png.exists():
        raise RuntimeError(f"Mermaid invalido en {src.name}:\n{r.stdout}\n{r.stderr}\n--- codigo ---\n{code}")
    return png


def build(md_path: Path, out_dir: Path) -> Path:
    text = md_path.read_text(encoding="utf-8")
    figs = {"n": 0}

    def repl_mermaid(m):
        code = m.group(1).strip("\n")
        png = render_mermaid(code, md_path)
        figs["n"] += 1
        cap = ""
        nxt = text[m.end():m.end() + 300].lstrip().split("\n", 1)[0]
        mcap = re.match(r"^\*?(Figura [^*]+)\*?$", nxt.strip())
        if mcap:
            cap = mcap.group(1)
        return f'\n\n<figure><img src="{png.as_uri()}"><figcaption>{html.escape(cap)}</figcaption></figure>\n\n'

    text2 = re.sub(r"```mermaid\n(.*?)```", repl_mermaid, text, flags=re.S)
    # quitar la linea de leyenda ya usada como figcaption
    text2 = re.sub(r"(</figure>\n+)\*?Figura [^\n]*\*?\n", r"\1", text2)

    # proteger matematicas de markdown
    stash = []

    def keep(m):
        stash.append(m.group(0))
        return f"@@M{len(stash)-1}@@"

    text2 = re.sub(r"\$\$.*?\$\$", keep, text2, flags=re.S)
    text2 = re.sub(r"(?<![\\\w])\$[^\$\n]+?\$", keep, text2)

    # imagenes relativas -> absolutas
    def abs_img(m):
        p = (md_path.parent / m.group(2)).resolve()
        return f"![{m.group(1)}]({p.as_uri()})" if p.exists() else m.group(0)
    text2 = re.sub(r"!\[([^\]]*)\]\(([^)\s:]+)\)", abs_img, text2)

    body = markdown.markdown(text2, extensions=["tables", "fenced_code", "sane_lists", "attr_list", "md_in_html"])
    body = re.sub(r"@@M(\d+)@@", lambda m: html.escape(stash[int(m.group(1))], quote=False), body)
    title = (re.search(r"^#\s+(.+)$", text, re.M) or [None, md_path.stem])[1]
    page = HTML.format(title=html.escape(title), css=CSS, body=body)

    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = out_dir / (md_path.stem + ".pdf")
    tmp = CACHE / (md_path.stem + ".html")
    tmp.write_text(page, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(tmp.as_uri(), wait_until="load")
        try:
            pg.wait_for_selector("body[data-ready='1']", timeout=15000)
            pg.wait_for_timeout(600)
        except Exception:
            pass
        footer = ('<div style="font-size:8px;width:100%;text-align:center;color:#667;">'
                  f'ITY SAS - Trabajo de grado (A. F. Lopez Russi) - {html.escape(md_path.stem.replace("_"," "))[:80]}'
                  ' - pag. <span class="pageNumber"></span>/<span class="totalPages"></span></div>')
        pg.pdf(path=str(pdf), format="A4", print_background=True, display_header_footer=True,
               header_template="<span></span>", footer_template=footer,
               margin={"top": "18mm", "bottom": "20mm", "left": "16mm", "right": "16mm"})
        b.close()
    print(f"OK {pdf.name}  ({pdf.stat().st_size//1024} KB, {figs['n']} diagramas)")
    return pdf


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = None
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        args = [a for a in args if a != str(out)]
    for a in args:
        mp = Path(a).resolve()
        build(mp, out or (mp.parent.parent if mp.parent.name == "fuentes" else mp.parent))
