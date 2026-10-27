import os
import sys
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

def md_to_html(md_text: str) -> str:
    lines = md_text.split("\n")
    html_lines = []
    in_table = False
    table_lines = []
    in_code = False
    code_lines = []
    in_list = False
    
    def flush_table(t_lines):
        if not t_lines:
            return ""
        out = ["<table>\n<thead>"]
        is_head = True
        for row in t_lines:
            cells = [c.strip() for c in row.split("|")[1:-1]]
            if all(set(c).issubset({"-", ":", " "}) for c in cells):
                is_head = False
                out.append("</thead>\n<tbody>")
                continue
            tag = "th" if is_head else "td"
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
        if is_head:
            out.append("</thead>")
        else:
            out.append("</tbody>")
        out.append("</table>")
        return "\n".join(out)

    for line in lines:
        sline = line.strip()
        
        # Check code fence
        if sline.startswith("```"):
            if in_code:
                in_code = False
                html_lines.append("<pre><code>" + "\n".join(code_lines) + "</code></pre>")
                code_lines = []
            else:
                in_code = True
                code_lines = []
            continue
        if in_code:
            code_lines.append(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            continue
            
        # Check table
        if sline.startswith("|") and sline.endswith("|"):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(sline)
            continue
        else:
            if in_table:
                in_table = False
                html_lines.append(flush_table(table_lines))
                table_lines = []
                
        # Check page break
        if "\\newpage" in sline:
            html_lines.append('<div class="page-break"></div>')
            continue
            
        # Check hr
        if sline == "---":
            html_lines.append('<hr style="border:0; border-top: 1px solid #cbd5e1; margin: 25px 0;">')
            continue
            
        # Check list item
        if sline.startswith("- ") or sline.startswith("* "):
            # Check if it's an italic figure caption like *Figura 1.1: ...*
            if sline.startswith("*Figura ") and sline.endswith("*"):
                # Handle figure insertion below
                pass
            else:
                if not in_list:
                    in_list = True
                    html_lines.append("<ul>")
                item_text = sline[2:]
                html_lines.append(f"<li>{item_text}</li>")
                continue
        elif in_list and (sline.startswith("1. ") or sline.startswith("2. ") or sline.startswith("3. ") or sline.startswith("4. ") or sline.startswith("5. ")):
            item_text = sline[3:]
            html_lines.append(f"<li>{item_text}</li>")
            continue
        else:
            if in_list and (not sline or not (sline.startswith("• ") or sline.startswith("<li>"))):
                in_list = False
                html_lines.append("</ul>")
                
        # Check headers
        if sline.startswith("# "):
            html_lines.append(f"<h1>{sline[2:]}</h1>")
            continue
        elif sline.startswith("## "):
            html_lines.append(f"<h2>{sline[3:]}</h2>")
            continue
        elif sline.startswith("### "):
            html_lines.append(f"<h3>{sline[4:]}</h3>")
            continue
        elif sline.startswith("#### "):
            html_lines.append(f"<h4>{sline[5:]}</h4>")
            continue
            
        # Check blockquote
        if sline.startswith("> "):
            html_lines.append(f'<div class="callout callout-info"><p>{sline[2:]}</p></div>')
            continue
            
        # Figure caption replacements with real images
        if sline.startswith("*Figura 1.1:"):
            caption = sline.strip("*")
            html_lines.append(f'<div class="figure-container"><img src="graficas/fig_08_diagrama_flujo_16_pasos.png" class="figure-image"><div class="figure-caption">{caption}</div></div>')
            continue
        elif sline.startswith("*Figura 2.1:"):
            caption = sline.strip("*")
            html_lines.append(f'<div class="figure-container"><img src="graficas/fig_04_matriz_priorizacion.png" class="figure-image"><div class="figure-caption">{caption}</div></div>')
            continue
        elif sline.startswith("*Figura 4.1:"):
            caption = sline.strip("*")
            html_lines.append(f'<div class="figure-container"><img src="graficas/fig_03_encuesta_likert.png" class="figure-image"><div class="figure-caption">{caption}</div></div>')
            continue
            
        # Empty line
        if not sline:
            continue
            
        # Regular paragraph
        html_lines.append(f"<p>{sline}</p>")
        
    if in_table:
        html_lines.append(flush_table(table_lines))
    if in_list:
        html_lines.append("</ul>")
        
    raw_html = "\n".join(html_lines)
    
    # Process inline formatting
    raw_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', raw_html)
    raw_html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', raw_html)
    raw_html = re.sub(r'`(.+?)`', r'<code>\1</code>', raw_html)
    
    # Extra figures injection after key sections
    extra_figs = {
        "<h3>5.1. Consolidación de Tiempos Agregados por Tipo de Formato</h3>": 
            '<h3>5.1. Consolidación de Tiempos Agregados por Tipo de Formato</h3>\n<div class="figure-container"><img src="graficas/fig_01_horas_por_fase.png" class="figure-image"><div class="figure-caption">Figura 5.1: Distribución Total de Horas por Fase y Formato en ITY SAS (N=315 piezas).</div></div>',
        "<h3>5.2. Análisis Detallado de Tiempos Promedio y Variabilidad por Pieza</h3>":
            '<h3>5.2. Análisis Detallado de Tiempos Promedio y Variabilidad por Pieza</h3>\n<div class="figure-container"><img src="graficas/fig_02_promedios_por_pieza.png" class="figure-image"><div class="figure-caption">Figura 5.2: Tiempos promedio unitarios por pieza y tasa media de revisiones por formato.</div></div>',
        "<h3>7.2. Presentación del VSM Agregado Global (N=315 Piezas)</h3>":
            '<h3>7.2. Presentación del VSM Agregado Global (N=315 Piezas)</h3>\n<div class="figure-container"><img src="graficas/fig_09_vsm_macro_diagram.png" class="figure-image"><div class="figure-caption">Figura 7.1: Value Stream Mapping (VSM) Macro Agregado del estado actual en ITY SAS (N=315 piezas).</div></div>',
        "<h3>8.4. Matriz Consolidada de Priorización de Restricciones Operativas</h3>":
            '<div class="figure-container"><img src="graficas/fig_04_matriz_priorizacion.png" class="figure-image"><div class="figure-caption">Figura 8.1: Matriz Estratégica de Priorización de Restricciones Operativas (ToC).</div></div>\n<h3>8.4. Matriz Consolidada de Priorización de Restricciones Operativas</h3>',
        "<h3>8.5. Análisis de Causa Raíz: Diagrama de Ishikawa 6M</h3>":
            '<h3>8.5. Análisis de Causa Raíz: Diagrama de Ishikawa 6M</h3>\n<div class="figure-container"><img src="graficas/fig_11_ishikawa_cuellos_botella.png" class="figure-image"><div class="figure-caption">Figura 8.2: Diagrama de Causa y Efecto (Ishikawa 6M) de las ineficiencias en ITY SAS.</div></div>',
        "<h3>9.2. Mapeo VSM del Microproceso de Edición de Video</h3>":
            '<h3>9.2. Mapeo VSM del Microproceso de Edición de Video</h3>\n<div class="figure-container"><img src="graficas/fig_10_vsm_micro_edicion.png" class="figure-image"><div class="figure-caption">Figura 9.1: Micro-VSM del subproceso de edición de Reels y bucle de retrabajo interno.</div></div>',
        "<h3>9.5. Simulación del Impacto de un Filtro de Calidad Previo Estandarizado</h3>":
            '<h3>9.5. Simulación del Impacto de un Filtro de Calidad Previo Estandarizado</h3>\n<div class="figure-container"><img src="graficas/fig_05_curva_edicion_retrabajo.png" class="figure-image"><div class="figure-caption">Figura 9.2: Curva del tiempo de ciclo esperado E[TC] en función de la probabilidad de rechazo en QC P(R1).</div></div>',
        "<h3>10.2. Evaluación de las Restricciones frente al Índice IA</h3>":
            '<h3>10.2. Evaluación de las Restricciones frente al Índice IA</h3>\n<div class="figure-container"><img src="graficas/fig_06_indice_automatizacion.png" class="figure-image"><div class="figure-caption">Figura 10.1: Evaluación de Factibilidad Técnica mediante Índice de Automatización (IA).</div></div>',
        "<h3>11.2. Mapeo de la Cadena de Valor Proyectada (VSM TO-BE)</h3>":
            '<h3>11.2. Mapeo de la Cadena de Valor Proyectada (VSM TO-BE)</h3>\n<div class="figure-container"><img src="graficas/fig_07_vsm_comparacion_as_is_to_be.png" class="figure-image"><div class="figure-caption">Figura 11.1: Comparativa de Tiempos de Ciclo y Lead Time: Escenario As-Is vs Estado Futuro To-Be.</div></div>'
    }
    
    for k, v in extra_figs.items():
        if k in raw_html:
            raw_html = raw_html.replace(k, v)
            
    return raw_html

def build_pdf():
    base_dir = Path("docs/documento_diagnostico").resolve()
    output_pdf = base_dir / "documento_diagnostico_vsm_toc.pdf"
    
    md_file = base_dir / "DOCUMENTO_DIAGNOSTICO_VSM_TOC.md"
    with open(md_file, "r", encoding="utf-8") as f:
        md_text = f.read()
        
    print("Convirtiendo Markdown completo a HTML...")
    body_html = md_to_html(md_text)
    
    css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

@page {
    size: A4 portrait;
    margin: 22mm 18mm 22mm 18mm;
    @bottom-right {
        content: counter(page);
    }
}

* { box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 9.5pt;
    line-height: 1.6;
    color: #1e293b;
    background-color: #ffffff;
    margin: 0;
    padding: 0;
}

.page-break { page-break-before: always; }
.avoid-break { page-break-inside: avoid; }

h1 {
    font-size: 15.5pt;
    font-weight: 800;
    color: #1e3a8a;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 6px;
    margin-top: 26px;
    margin-bottom: 14px;
    page-break-after: avoid;
}

h2 {
    font-size: 12pt;
    font-weight: 700;
    color: #0f172a;
    margin-top: 20px;
    margin-bottom: 10px;
    page-break-after: avoid;
}

h3 {
    font-size: 10.5pt;
    font-weight: 600;
    color: #334155;
    margin-top: 16px;
    margin-bottom: 8px;
    page-break-after: avoid;
}

h4 {
    font-size: 9.5pt;
    font-weight: 600;
    color: #475569;
    margin-top: 12px;
    margin-bottom: 6px;
    page-break-after: avoid;
}

p {
    margin-top: 0;
    margin-bottom: 11px;
    text-align: justify;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 8pt;
    page-break-inside: avoid;
}

th, td {
    padding: 5.5px 8.5px;
    border: 1px solid #cbd5e1;
    text-align: left;
}

th {
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 700;
    text-transform: uppercase;
    font-size: 7.5pt;
    letter-spacing: 0.5px;
}

tr:nth-child(even) { background-color: #f8fafc; }

.callout {
    padding: 12px 16px;
    border-radius: 6px;
    margin: 14px 0;
    border-left: 4px solid;
    page-break-inside: avoid;
}

.callout-info {
    background-color: #f0f9ff;
    border-color: #0284c7;
    color: #0369a1;
}

.figure-container {
    text-align: center;
    margin: 18px 0;
    page-break-inside: avoid;
}

.figure-image {
    max-width: 95%;
    max-height: 480px;
    height: auto;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.figure-caption {
    font-size: 8pt;
    color: #64748b;
    margin-top: 5px;
    font-style: italic;
}

pre {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 9px 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 7.5pt;
    line-height: 1.4;
    overflow-x: auto;
    page-break-inside: avoid;
}

code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8pt;
    background-color: #f1f5f9;
    padding: 1px 4px;
    border-radius: 3px;
    color: #0f172a;
}

ul, ol {
    margin-top: 0;
    margin-bottom: 11px;
    padding-left: 20px;
}

li { margin-bottom: 3px; }
"""

    full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Diagnóstico Operativo VSM y ToC - ITY SAS</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function() {{
    renderMathInElement(document.body, {{
        delimiters: [
            {{left: "$$", right: "$$", display: true}},
            {{left: "$", right: "$", display: false}}
        ]
    }});
}});
</script>
<style>
{css}
</style>
</head>
<body>
{body_html}
</body>
</html>
"""

    html_file = base_dir / "temp_diagnostico.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(full_html)
        
    print(f"HTML generado ({html_file.stat().st_size:,} bytes). Iniciando Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_file.as_uri(), wait_until="load", timeout=90000)
        page.wait_for_timeout(2500) # Espera KaTeX
        
        page.pdf(
            path=str(output_pdf),
            format="A4",
            print_background=True,
            margin={
                "top": "18mm",
                "right": "14mm",
                "bottom": "20mm",
                "left": "14mm"
            },
            display_header_footer=True,
            header_template='<div style="font-size: 7.5pt; color: #64748b; width: 100%; padding: 0 16mm; display: flex; justify-content: space-between; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px;"><span>ITY SAS &bull; Documento de Diagnóstico Operativo (VSM & ToC)</span><span>Producto Técnico 2.1 (OE1)</span></div>',
            footer_template='<div style="font-size: 7.5pt; color: #64748b; width: 100%; padding: 0 16mm; display: flex; justify-content: space-between; border-top: 1px solid #e2e8f0; padding-top: 4px;"><span>Universidad Católica de Colombia &bull; Facultad de Ingeniería</span><span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span></div>'
        )
        browser.close()
        
    if html_file.exists():
        html_file.unlink()
        
    print(f"ÉXITO: PDF generado en {output_pdf}")
    print(f"Tamaño: {output_pdf.stat().st_size:,} bytes")
    
    with open(output_pdf, 'rb') as f:
        pdf_bytes = f.read()
    page_count = len(re.findall(rb'/Type\s*/Page\b', pdf_bytes))
    print(f"TOTAL EXACTO DE PÁGINAS COMPILADAS EN EL PDF: {page_count} páginas")

if __name__ == "__main__":
    build_pdf()
