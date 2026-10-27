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
        out = ['<table class="data-table">\n<thead>']
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
            
        if sline.startswith("> "):
            html_lines.append(f'<blockquote class="doc-quote">{sline[2:]}</blockquote>')
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
    
    # Highlight IE badges
    for i in range(1, 11):
        ie_id = f"IE-{i:02d}"
        raw_html = raw_html.replace(f"[{ie_id}]", f'<span class="badge-ie">[{ie_id}]</span>')
        raw_html = raw_html.replace(f"`{ie_id}`", f'<span class="badge-ie">{ie_id}</span>')
        
    return raw_html

def build_pdf():
    base_dir = Path("docs/interfaces").resolve()
    output_pdf = base_dir / "anexo_14_interfaces_externas.pdf"
    md_file = base_dir / "ANEXO_14_ESPECIFICACION_INTERFACES_EXTERNAS.md"
    
    print(f"Leyendo Markdown desde: {md_file}")
    with open(md_file, "r", encoding="utf-8") as f:
        md_text = f.read()
        
    print("Convirtiendo Markdown a HTML con estilos formales de ingeniería...")
    body_html = md_to_html(md_text)
    
    cover_html = """
    <div class="cover-page">
        <div class="cover-header">
            <div class="institution">UNIVERSIDAD CATÓLICA DE COLOMBIA</div>
            <div class="faculty">FACULTAD DE INGENIERÍA</div>
            <div class="program">PROGRAMA DE INGENIERÍA DE SISTEMAS Y COMPUTACIÓN</div>
        </div>
        
        <div class="cover-body">
            <div class="deliverable-badge">PRODUCTO TÉCNICO FORMAL &bull; ANEXO 14</div>
            <h1 class="cover-title">ESPECIFICACIÓN DE INTERFACES EXTERNAS (APIs)</h1>
            <h2 class="cover-subtitle">
                Fichas Técnicas Resumidas de las 10 Interfaces, Justificación Arquitectónica de Postiz para el Agente de Ideación y Publicación, Contratos OpenAPI 3.0.3 y Guía de Ejecución Postman
            </h2>
            <div class="cover-project-box">
                <strong>Proyecto de Grado:</strong> Prueba de concepto de un sistema multiagente basado en microservicios y contenedores para la automatización de la planificación y la publicación de contenido en la empresa ITY SAS
            </div>
        </div>
        
        <div class="cover-footer">
            <div class="author-block">
                <strong>Autor:</strong> Alvaro Felipe Lopez Russi<br>
                <strong>Código Estudiantil:</strong> 67000867<br>
                <strong>Correo Institucional:</strong> aflopez67@ucatolica.edu.co
            </div>
            <div class="advisor-block">
                <strong>Entidad Patrocinadora / Caso de Estudio:</strong> ITY SAS<br>
                <strong>Estándares de Referencia:</strong> OpenAPI 3.0.3 &bull; IEEE Std 830-1998 &bull; ISO/IEC/IEEE 42010
            </div>
            <div class="cover-date">
                Bogotá D.C., Octubre 2026 &bull; Versión 1.0 Oficial
            </div>
        </div>
    </div>
    <div class="page-break"></div>
    """
    
    css = """
    @page {
        size: A4 portrait;
        margin: 22mm 18mm 22mm 18mm;
    }
    
    * { box-sizing: border-box; }
    
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 9.5pt;
        line-height: 1.6;
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
        padding: 30px 10px;
        page-break-after: always;
    }
    
    .cover-header .institution {
        font-size: 16pt;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: 1.5px;
    }
    
    .cover-header .faculty {
        font-size: 12pt;
        font-weight: 600;
        color: #1e3a8a;
        margin-top: 4px;
    }
    
    .cover-header .program {
        font-size: 10.5pt;
        font-weight: 500;
        color: #475569;
        margin-top: 2px;
    }
    
    .cover-body {
        margin: 40px 0;
    }
    
    .deliverable-badge {
        display: inline-block;
        background: #1e3a8a;
        color: #ffffff;
        font-size: 9pt;
        font-weight: 700;
        letter-spacing: 1px;
        padding: 6px 16px;
        border-radius: 20px;
        margin-bottom: 24px;
    }
    
    .cover-title {
        font-size: 21pt;
        font-weight: 900;
        color: #0f172a;
        line-height: 1.25;
        margin: 0 0 16px 0;
    }
    
    .cover-subtitle {
        font-size: 11pt;
        font-weight: 400;
        color: #334155;
        line-height: 1.5;
        max-width: 650px;
        margin: 0 auto 30px auto;
    }
    
    .cover-project-box {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-left: 5px solid #2563eb;
        padding: 14px 20px;
        text-align: left;
        max-width: 680px;
        margin: 0 auto;
        font-size: 9.5pt;
        color: #334155;
        border-radius: 4px;
    }
    
    .cover-footer {
        display: flex;
        flex-direction: column;
        gap: 12px;
        border-top: 1px solid #e2e8f0;
        padding-top: 20px;
        font-size: 9pt;
        color: #475569;
    }
    
    .author-block, .advisor-block {
        line-height: 1.5;
    }
    
    .cover-date {
        font-weight: 600;
        color: #1e293b;
        margin-top: 8px;
    }
    
    .title-h1 {
        font-size: 16pt;
        font-weight: 800;
        color: #1e3a8a;
        border-bottom: 2.5px solid #2563eb;
        padding-bottom: 6px;
        margin-top: 30px;
        margin-bottom: 16px;
        page-break-after: avoid;
    }
    
    .section-h2 {
        font-size: 12.5pt;
        font-weight: 700;
        color: #0f172a;
        border-bottom: 1px solid #cbd5e1;
        padding-bottom: 4px;
        margin-top: 24px;
        margin-bottom: 12px;
        page-break-after: avoid;
    }
    
    .subsection-h3 {
        font-size: 10.5pt;
        font-weight: 600;
        color: #1e3a8a;
        margin-top: 18px;
        margin-bottom: 8px;
        page-break-after: avoid;
    }
    
    .subsubsection-h4 {
        font-size: 9.5pt;
        font-weight: 600;
        color: #475569;
        margin-top: 14px;
        margin-bottom: 6px;
        page-break-after: avoid;
    }
    
    p {
        margin: 0 0 10px 0;
        text-align: justify;
    }
    
    .data-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 8.5pt;
        margin: 14px 0 18px 0;
        page-break-inside: avoid;
    }
    
    .data-table th {
        background-color: #1e3a8a;
        color: #ffffff;
        font-weight: 600;
        padding: 7px 10px;
        border: 1px solid #cbd5e1;
        text-align: left;
    }
    
    .data-table td {
        padding: 6px 10px;
        border: 1px solid #e2e8f0;
        vertical-align: top;
        line-height: 1.45;
    }
    
    .data-table tbody tr:nth-child(even) {
        background-color: #f8fafc;
    }
    
    .data-table tbody tr:hover {
        background-color: #f1f5f9;
    }
    
    .code-box {
        background-color: #0f172a;
        color: #f8fafc;
        font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
        font-size: 8pt;
        line-height: 1.4;
        padding: 12px 14px;
        border-radius: 6px;
        border: 1px solid #334155;
        overflow-x: auto;
        margin: 12px 0 16px 0;
        page-break-inside: avoid;
    }
    
    .inline-code {
        font-family: Consolas, "Courier New", monospace;
        font-size: 8.5pt;
        background-color: #f1f5f9;
        color: #0f172a;
        padding: 1px 5px;
        border-radius: 3px;
        border: 1px solid #cbd5e1;
    }
    
    .badge-ie {
        display: inline-block;
        background-color: #eff6ff;
        color: #1d4ed8;
        font-weight: 700;
        font-family: Consolas, monospace;
        padding: 1px 6px;
        border-radius: 4px;
        border: 1px solid #bfdbfe;
    }
    
    .doc-list {
        margin: 6px 0 12px 0;
        padding-left: 22px;
    }
    
    .doc-list li {
        margin-bottom: 4px;
        line-height: 1.5;
        text-align: justify;
    }
    
    .doc-quote {
        border-left: 4px solid #3b82f6;
        background-color: #eff6ff;
        color: #1e3a8a;
        padding: 8px 14px;
        margin: 12px 0;
        font-style: italic;
        border-radius: 0 4px 4px 0;
    }
    
    .divider {
        border: 0;
        border-top: 1px solid #cbd5e1;
        margin: 22px 0;
    }
    """
    
    full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Anexo 14: Especificación de Interfaces Externas (APIs)</title>
    <style>{css}</style>
</head>
<body>
    {cover_html}
    {body_html}
</body>
</html>"""
    
    html_file = base_dir / "anexo_14_temp.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"HTML temporal generado: {html_file}")
    
    print("Iniciando Playwright para compilar PDF...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_file.as_uri(), wait_until="load", timeout=90000)
        
        header_template = """
        <div style="font-size: 7pt; color: #64748b; font-family: sans-serif; width: 100%; display: flex; justify-content: space-between; padding: 0 18mm;">
            <span>UNIVERSIDAD CATÓLICA DE COLOMBIA &bull; FACULTAD DE INGENIERÍA</span>
            <span>ANEXO 14: ESPECIFICACIÓN DE INTERFACES EXTERNAS (APIs)</span>
        </div>
        """
        
        footer_template = """
        <div style="font-size: 7.5pt; color: #64748b; font-family: sans-serif; width: 100%; display: flex; justify-content: space-between; padding: 0 18mm;">
            <span>ITY SAS &bull; Sistema Multiagente de Planificación y Publicación</span>
            <span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span>
        </div>
        """
        
        page.pdf(
            path=str(output_pdf),
            format="A4",
            print_background=True,
            margin={"top": "22mm", "bottom": "22mm", "left": "18mm", "right": "18mm"},
            display_header_footer=True,
            header_template=header_template,
            footer_template=footer_template
        )
        browser.close()
        
    print(f"PDF generado con éxito en: {output_pdf}")
    if os.path.exists(html_file):
        os.remove(html_file)
        
    size_mb = os.path.getsize(output_pdf) / (1024 * 1024)
    print(f"Tamaño del archivo PDF: {size_mb:.2f} MB")

if __name__ == "__main__":
    build_pdf()
