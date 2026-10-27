import os
import sys
import re
import shutil
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
        out = ['<table class="arch-table">\n<thead>']
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
                html_lines.append('<pre class="code-box"><code>' + "\n".join(code_lines) + "</code></pre>")
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
            html_lines.append('<hr class="divider">')
            continue
            
        # Check list item
        if sline.startswith("- ") or sline.startswith("* "):
            if not in_list:
                in_list = True
                html_lines.append('<ul class="doc-list">')
            item_text = sline[2:]
            html_lines.append(f"<li>{item_text}</li>")
            continue
        elif in_list and (sline.startswith("1. ") or sline.startswith("2. ") or sline.startswith("3. ") or sline.startswith("4. ") or sline.startswith("5. ") or sline.startswith("6. ")):
            item_text = sline[3:]
            html_lines.append(f"<li>{item_text}</li>")
            continue
        else:
            if in_list and (not sline or not (sline.startswith("• ") or sline.startswith("<li>"))):
                in_list = False
                html_lines.append("</ul>")
                
        # Check headers
        if sline.startswith("# "):
            html_lines.append(f'<h1 class="title-h1">{sline[2:]}</h1>')
            continue
        if sline.startswith("## "):
            html_lines.append(f'<h2 class="section-h2">{sline[3:]}</h2>')
            continue
        if sline.startswith("### "):
            html_lines.append(f'<h3 class="subsection-h3">{sline[4:]}</h3>')
            continue
        if sline.startswith("#### "):
            html_lines.append(f'<h4 class="subsubsection-h4">{sline[5:]}</h4>')
            continue
            
        # Math display
        if sline.startswith("$$") and sline.endswith("$$") and len(sline) > 2:
            math_expr = sline[2:-2].strip()
            html_lines.append(f'<div class="display-math">{math_expr}</div>')
            continue
            
        # Check blockquote
        if sline.startswith("> "):
            html_lines.append(f'<blockquote class="doc-quote">{sline[2:]}</blockquote>')
            continue
            
        # Pass raw div or img tags
        if sline.startswith("<div") or sline.startswith("</div") or sline.startswith("<img") or sline == "<br>":
            html_lines.append(sline)
            continue
            
        if not sline:
            continue
            
        html_lines.append(f"<p>{sline}</p>")
        
    if in_table:
        html_lines.append(flush_table(table_lines))
    if in_list:
        html_lines.append("</ul>")
        
    raw_html = "\n".join(html_lines)
    
    # Inline formatting replacements
    raw_html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", raw_html)
    raw_html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", raw_html)
    raw_html = re.sub(r"`(.*?)`", r'<code class="inline-code">\1</code>', raw_html)
    
    # Math inline: $...$
    raw_html = re.sub(r"\$([^\$\n]+)\$", r'<span class="inline-math">\1</span>', raw_html)
    
    # Clean up figure containers around <img>
    raw_html = re.sub(
        r'<div align="center">\s*<img src="([^"]+)" alt="([^"]*)"[^>]*/>\s*<p><em>([^<]*)</em></p>\s*</div>',
        r'<div class="figure-container"><img src="\1" class="figure-image"/><div class="figure-caption">\3</div></div>',
        raw_html
    )
    
    return raw_html

def build_pdf():
    base_dir = Path("docs/documento_arquitectura").resolve()
    output_pdf = base_dir / "documento_arquitectura.pdf"
    docs_pdf = Path("docs/documento_arquitectura.pdf").resolve()
    md_file = base_dir / "DOCUMENTO_ARQUITECTURA.md"
    
    print(f"Leyendo Markdown de arquitectura desde: {md_file}")
    with open(md_file, "r", encoding="utf-8") as f:
        md_text = f.read()
        
    print("Convirtiendo Markdown a HTML con estilos formales arc42 e IEEE...")
    body_html = md_to_html(md_text)
    
    cover_html = """
    <div class="cover-page">
        <div class="cover-header">
            <div class="institution">UNIVERSIDAD CATÓLICA DE COLOMBIA</div>
            <div class="faculty">FACULTAD DE INGENIERÍA</div>
            <div class="program">PROGRAMA DE INGENIERÍA DE SISTEMAS Y COMPUTACIÓN</div>
        </div>
        
        <div class="cover-body">
            <div class="logo-box">
                <img src="images/arc42-logo.png" style="width: 200px; margin-bottom: 20px;"/>
            </div>
            <div class="deliverable-badge">DOCUMENTO TÉCNICO FORMAL &bull; ARQUITECTURA DE SOFTWARE (SAD)</div>
            <h1 class="cover-title">SISTEMA MULTIAGENTE BASADO EN MICROSERVICIOS Y CONTENEDORES PARA LA AUTOMATIZACIÓN DE LA PRODUCCIÓN Y PUBLICACIÓN DE CONTENIDO DIGITAL</h1>
            <h2 class="cover-subtitle">
                Descripción Formal de Arquitectura según la Plantilla arc42 (Versión 7.0 ES), ISO/IEC/IEEE 42010:2022 y Alineación Integral con la SRS IEEE Std 830-1998
            </h2>
            <div class="cover-project-box">
                <strong>Empresa Caso de Estudio:</strong> ITY SAS (Bogotá D.C., Colombia)<br>
                <strong>Alcance del Proyecto:</strong> Prueba de Concepto (PoC) en Microservicios Docker &bull; Mitigación de Cuellos de Botella ToC (R1, R2, R3) &bull; Cumplimiento OE2 y OE3
            </div>
        </div>
        
        <div class="cover-footer">
            <div class="author-block">
                <strong>Autor:</strong> Alvaro Felipe Lopez Russi &bull; Código: 67000867 &bull; aflopez67@ucatolica.edu.co<br>
                <strong>Director / Asesor Metodológico:</strong> Docente Titular de Grado
            </div>
            <div class="advisor-block">
                <strong>Modelos de Vistas:</strong> C4 Model (Niveles 1 a 4) &bull; Metodología Gaia &bull; AUML &bull; BDI &bull; ATAM &bull; ADR (001-007)
            </div>
            <div class="cover-date">
                Bogotá D.C., Octubre 2026 &bull; Versión 3.0 Oficial
            </div>
        </div>
    </div>
    <div class="page-break"></div>
    """
    
    css = """
    @page {
        size: A4 portrait;
        margin: 20mm 16mm 20mm 16mm;
    }
    
    * { box-sizing: border-box; }
    
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 9pt;
        line-height: 1.55;
        color: #1e293b;
        background-color: #ffffff;
        margin: 0;
        padding: 0;
    }
    
    .page-break { page-break-before: always; }
    
    .cover-page {
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        text-align: center;
        padding: 25px 10px;
        page-break-after: always;
    }
    
    .cover-header .institution {
        font-size: 15pt;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: 1.5px;
    }
    
    .cover-header .faculty {
        font-size: 11.5pt;
        font-weight: 600;
        color: #1e3a8a;
        margin-top: 4px;
    }
    
    .cover-header .program {
        font-size: 10pt;
        font-weight: 500;
        color: #475569;
        margin-top: 2px;
    }
    
    .cover-body {
        margin: 25px 0;
    }
    
    .deliverable-badge {
        display: inline-block;
        background: #1e3a8a;
        color: #ffffff;
        font-size: 8.5pt;
        font-weight: 700;
        letter-spacing: 1px;
        padding: 5px 15px;
        border-radius: 20px;
        margin-bottom: 18px;
    }
    
    .cover-title {
        font-size: 18pt;
        font-weight: 900;
        color: #0f172a;
        line-height: 1.25;
        margin: 0 0 14px 0;
    }
    
    .cover-subtitle {
        font-size: 10.5pt;
        font-weight: 400;
        color: #334155;
        line-height: 1.5;
        max-width: 650px;
        margin: 0 auto 25px auto;
    }
    
    .cover-project-box {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-left: 5px solid #2563eb;
        padding: 12px 18px;
        text-align: left;
        max-width: 680px;
        margin: 0 auto;
        font-size: 9pt;
        color: #334155;
        border-radius: 4px;
    }
    
    .cover-footer {
        display: flex;
        flex-direction: column;
        gap: 10px;
        border-top: 1px solid #e2e8f0;
        padding-top: 16px;
        font-size: 8.5pt;
        color: #475569;
    }
    
    .author-block, .advisor-block {
        line-height: 1.45;
    }
    
    .cover-date {
        font-weight: 600;
        color: #1e293b;
        margin-top: 4px;
    }
    
    .title-h1 {
        font-size: 15pt;
        font-weight: 800;
        color: #1e3a8a;
        border-bottom: 2.5px solid #2563eb;
        padding-bottom: 5px;
        margin-top: 26px;
        margin-bottom: 14px;
        page-break-after: avoid;
    }
    
    .section-h2 {
        font-size: 12pt;
        font-weight: 700;
        color: #0f172a;
        border-bottom: 1px solid #cbd5e1;
        padding-bottom: 4px;
        margin-top: 20px;
        margin-bottom: 10px;
        page-break-after: avoid;
    }
    
    .subsection-h3 {
        font-size: 10pt;
        font-weight: 600;
        color: #1e3a8a;
        margin-top: 16px;
        margin-bottom: 6px;
        page-break-after: avoid;
    }
    
    .subsubsection-h4 {
        font-size: 9pt;
        font-weight: 600;
        color: #475569;
        margin-top: 12px;
        margin-bottom: 5px;
        page-break-after: avoid;
    }
    
    p {
        margin: 0 0 9px 0;
        text-align: justify;
    }
    
    .arch-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 8pt;
        margin: 12px 0 16px 0;
        page-break-inside: avoid;
    }
    
    .arch-table th {
        background-color: #1e3a8a;
        color: #ffffff;
        font-weight: 600;
        padding: 6px 8px;
        border: 1px solid #cbd5e1;
        text-align: left;
    }
    
    .arch-table td {
        padding: 5px 8px;
        border: 1px solid #e2e8f0;
        vertical-align: top;
        line-height: 1.4;
    }
    
    .arch-table tbody tr:nth-child(even) {
        background-color: #f8fafc;
    }
    
    .arch-table tbody tr:hover {
        background-color: #f1f5f9;
    }
    
    .code-box {
        background-color: #0f172a;
        color: #f8fafc;
        font-family: Consolas, "Courier New", monospace;
        font-size: 7.5pt;
        line-height: 1.35;
        padding: 10px 12px;
        border-radius: 5px;
        border: 1px solid #334155;
        overflow-x: auto;
        margin: 10px 0 14px 0;
        page-break-inside: avoid;
    }
    
    .inline-code {
        font-family: Consolas, "Courier New", monospace;
        font-size: 8pt;
        background-color: #f1f5f9;
        color: #0f172a;
        padding: 1px 4px;
        border-radius: 3px;
        border: 1px solid #cbd5e1;
    }
    
    .inline-math {
        font-family: "Cambria Math", "Times New Roman", serif;
        font-style: italic;
        background: #f8fafc;
        padding: 0 2px;
    }
    
    .display-math {
        font-family: "Cambria Math", "Times New Roman", serif;
        text-align: center;
        background: #f8fafc;
        border-left: 3px solid #2563eb;
        padding: 8px;
        margin: 10px 0;
        font-size: 9.5pt;
    }
    
    .doc-list {
        margin: 4px 0 10px 0;
        padding-left: 20px;
    }
    
    .doc-list li {
        margin-bottom: 3px;
        line-height: 1.45;
        text-align: justify;
    }
    
    .doc-quote {
        border-left: 4px solid #3b82f6;
        background-color: #eff6ff;
        color: #1e3a8a;
        padding: 8px 12px;
        margin: 10px 0;
        font-style: italic;
        border-radius: 0 4px 4px 0;
    }
    
    .figure-container {
        text-align: center;
        margin: 14px 0 18px 0;
        page-break-inside: avoid;
    }
    
    .figure-image {
        max-width: 95%;
        height: auto;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        padding: 4px;
        background: #ffffff;
    }
    
    .figure-caption {
        font-size: 8pt;
        color: #475569;
        font-style: italic;
        margin-top: 5px;
    }
    
    .divider {
        border: 0;
        border-top: 1px solid #cbd5e1;
        margin: 18px 0;
    }
    """
    
    full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Documento de Arquitectura de Software (SAD) - ITY SAS</title>
    <style>{css}</style>
</head>
<body>
    {cover_html}
    {body_html}
</body>
</html>"""
    
    html_file = base_dir / "documento_arquitectura_temp.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"HTML temporal generado: {html_file}")
    
    print("Iniciando Playwright para compilar PDF de Arquitectura...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_file.as_uri(), wait_until="load", timeout=120000)
        
        header_template = """
        <div style="font-size: 6.5pt; color: #64748b; font-family: sans-serif; width: 100%; display: flex; justify-content: space-between; padding: 0 16mm;">
            <span>UNIVERSIDAD CATÓLICA DE COLOMBIA &bull; FACULTAD DE INGENIERÍA</span>
            <span>DOCUMENTO DE ARQUITECTURA DE SOFTWARE (arc42 v7 &bull; ISO/IEC/IEEE 42010)</span>
        </div>
        """
        
        footer_template = """
        <div style="font-size: 7pt; color: #64748b; font-family: sans-serif; width: 100%; display: flex; justify-content: space-between; padding: 0 16mm;">
            <span>ITY SAS &bull; Sistema Multiagente de Planificación y Publicación (OE2 / OE3)</span>
            <span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span>
        </div>
        """
        
        page.pdf(
            path=str(output_pdf),
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm", "left": "16mm", "right": "16mm"},
            display_header_footer=True,
            header_template=header_template,
            footer_template=footer_template
        )
        browser.close()
        
    print(f"PDF generado con éxito en: {output_pdf}")
    if os.path.exists(html_file):
        os.remove(html_file)
        
    size_mb = os.path.getsize(output_pdf) / (1024 * 1024)
    print(f"Tamaño del archivo PDF en documento_arquitectura/: {size_mb:.2f} MB")
    
    # Copiar también directamente a docs/documento_arquitectura.pdf
    shutil.copyfile(output_pdf, docs_pdf)
    print(f"Copia canónica guardada directamente en: {docs_pdf}")

if __name__ == "__main__":
    build_pdf()
