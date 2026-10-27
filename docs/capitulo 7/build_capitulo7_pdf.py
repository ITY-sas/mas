import os
import sys
import re
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

def parse_tex_to_html(tex_content: str, base_dir: Path) -> str:
    # Extract content between \begin{document} and \end{document}
    doc_match = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", tex_content, re.DOTALL)
    if doc_match:
        content = doc_match.group(1)
    else:
        content = tex_content

    # Remove comments (lines starting with %)
    content = re.sub(r"^[ \t]*%[^\n]*\n?", "", content, flags=re.MULTILINE)
    
    # Text replacements
    content = content.replace("<<", "«").replace(">>", "»")
    content = content.replace("``", "“").replace("''", "”")
    content = content.replace(r"\LaTeX{}", "LaTeX")
    content = content.replace(r"\%", "%")
    content = content.replace(r"\&", "&")
    
    # Process lstlisting blocks first
    code_blocks = []
    def save_code(match):
        code_text = match.group(1).strip()
        code_text = code_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        idx = len(code_blocks)
        code_blocks.append(f'<pre class="code-box"><code>{code_text}</code></pre>')
        return f"__CODE_BLOCK_{idx}__"
        
    content = re.sub(r"\\begin\{lstlisting\}(?:\[[^\]]*\])?(.*?)\\end\{lstlisting\}", save_code, content, flags=re.DOTALL)

    # Process figures
    figure_blocks = []
    def save_figure(match):
        fig_body = match.group(0)
        img_match = re.search(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", fig_body)
        cap_match = re.search(r"\\caption\{([^}]+)\}", fig_body)
        
        img_src = ""
        caption_text = ""
        if img_match:
            img_path = img_match.group(1).strip()
            # replace .pdf with .png
            if img_path.endswith(".pdf"):
                img_path = img_path[:-4] + ".png"
            elif not img_path.endswith(".png"):
                img_path = img_path + ".png"
            img_src = img_path
            
        if cap_match:
            caption_text = cap_match.group(1).strip()
            # clean latex inside caption
            caption_text = re.sub(r"\\code\{([^}]+)\}", r"<code>\1</code>", caption_text)
            caption_text = re.sub(r"\\texttt\{([^}]+)\}", r"<code>\1</code>", caption_text)
            caption_text = re.sub(r"\\textbf\{([^}]+)\}", r"<strong>\1</strong>", caption_text)
            caption_text = re.sub(r"\\textit\{([^}]+)\}", r"<em>\1</em>", caption_text)
            caption_text = re.sub(r"\$([^$]+)\$", r"<i>\1</i>", caption_text)
            caption_text = caption_text.replace(r"\_", "_")
            
        idx = len(figure_blocks)
        figure_blocks.append(
            f'<div class="figure-container">'
            f'<img src="{img_src}" class="figure-image"/>'
            f'<div class="figure-caption">{caption_text}</div>'
            f'</div>'
        )
        return f"__FIGURE_BLOCK_{idx}__"

    content = re.sub(r"\\begin\{figure\}(?:\[[^\]]*\])?.*?\\end\{figure\}", save_figure, content, flags=re.DOTALL)

    # Process tables (longtable, table, tabularx)
    table_blocks = []
    def save_table(match):
        table_body = match.group(0)
        cap_match = re.search(r"\\caption\{([^}]+)\}", table_body)
        caption_text = ""
        if cap_match:
            caption_text = cap_match.group(1).strip()
            caption_text = re.sub(r"\\code\{([^}]+)\}", r"<code>\1</code>", caption_text)
            caption_text = re.sub(r"\\textbf\{([^}]+)\}", r"<strong>\1</strong>", caption_text)
            caption_text = re.sub(r"\\textit\{([^}]+)\}", r"<em>\1</em>", caption_text)
            caption_text = re.sub(r"\$([^$]+)\$", r"<i>\1</i>", caption_text)
            caption_text = caption_text.replace(r"\_", "_")
            
        # Extract rows
        rows_match = re.search(r"\\begin\{(?:longtable|tabularx|tabular)\}(?:\{[^}]*\})?(?:\{[^}]*\})?(.*?)\\end\{(?:longtable|tabularx|tabular)\}", table_body, re.DOTALL)
        if not rows_match:
            return ""
        raw_rows = rows_match.group(1)
        
        # Split by \\
        lines = [r.strip() for r in raw_rows.split(r"\\")]
        html_rows = []
        is_first_header = True
        
        for r in lines:
            r = r.strip()
            if not r or r.startswith(r"\toprule") or r.startswith(r"\bottomrule") or r.startswith(r"\midrule") or r.startswith(r"\endhead") or r.startswith(r"\endfirsthead") or r.startswith(r"\endfoot") or r.startswith(r"\endlastfoot") or r.startswith(r"\caption") or r.startswith(r"\label"):
                continue
            r = r.replace(r"\addlinespace", "")
            r = r.replace(r"\hline", "")
            r = r.strip()
            if not r:
                continue
                
            cells = [c.strip() for c in r.split("&")]
            clean_cells = []
            for c in cells:
                c = re.sub(r"\\code\{([^}]+)\}", r"<code>\1</code>", c)
                c = re.sub(r"\\texttt\{([^}]+)\}", r"<code>\1</code>", c)
                c = re.sub(r"\\textbf\{([^}]+)\}", r"<strong>\1</strong>", c)
                c = re.sub(r"\\textit\{([^}]+)\}", r"<em>\1</em>", c)
                c = re.sub(r"\\newline", r"<br>", c)
                c = re.sub(r"\$([^$]+)\$", r"<i>\1</i>", c)
                c = c.replace(r"\_", "_")
                clean_cells.append(c)
                
            tag = "th" if is_first_header else "td"
            html_rows.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in clean_cells) + "</tr>")
            is_first_header = False
            
        cap_html = f'<div class="table-caption">{caption_text}</div>' if caption_text else ""
        table_html = f'<div class="table-container">{cap_html}<table class="arch-table">\n' + "\n".join(html_rows) + '\n</table></div>'
        idx = len(table_blocks)
        table_blocks.append(table_html)
        return f"__TABLE_BLOCK_{idx}__"

    content = re.sub(r"\\begin\{longtable\}.*?\\end\{longtable\}", save_table, content, flags=re.DOTALL)
    content = re.sub(r"\\begin\{table\}.*?\\end\{table\}", save_table, content, flags=re.DOTALL)

    # Process math equations
    math_blocks = []
    def save_math(match):
        m_expr = match.group(1).strip()
        idx = len(math_blocks)
        math_blocks.append(f'<div class="display-math">{m_expr}</div>')
        return f"__MATH_BLOCK_{idx}__"
    content = re.sub(r"\\begin\{equation\}(.*?)\\end\{equation\}", save_math, content, flags=re.DOTALL)
    content = re.sub(r"\\\[(.*?)\\\]", save_math, content, flags=re.DOTALL)

    # Headings
    content = re.sub(r"\\chapter\{([^}]+)\}(?:\\label\{[^}]*\})?", r'<h1 class="chapter-h1">\1</h1>', content)
    content = re.sub(r"\\section\{([^}]+)\}(?:\\label\{[^}]*\})?", r'<h2 class="section-h2">\1</h2>', content)
    content = re.sub(r"\\subsection\{([^}]+)\}(?:\\label\{[^}]*\})?", r'<h3 class="subsection-h3">\1</h3>', content)
    content = re.sub(r"\\subsubsection\*?\{([^}]+)\}(?:\\label\{[^}]*\})?", r'<h4 class="subsubsection-h4">\1</h4>', content)

    # Clean inlines
    content = re.sub(r"\\code\{([^}]+)\}", r'<code class="inline-code">\1</code>', content)
    content = re.sub(r"\\texttt\{([^}]+)\}", r'<code class="inline-code">\1</code>', content)
    content = re.sub(r"\\textbf\{([^}]+)\}", r'<strong>\1</strong>', content)
    content = re.sub(r"\\textit\{([^}]+)\}", r'<em>\1</em>', content)
    content = re.sub(r"\\emph\{([^}]+)\}", r'<em>\1</em>', content)
    content = re.sub(r"\\underline\{([^}]+)\}", r'<u>\1</u>', content)
    content = re.sub(r"\\ref\{fig:([^}]+)\}", r'Figura \1', content)
    content = re.sub(r"\\ref\{tab:([^}]+)\}", r'Tabla \1', content)
    content = re.sub(r"\\ref\{sec:([^}]+)\}", r'Sección \1', content)
    content = re.sub(r"\\ref\{chap:([^}]+)\}", r'Capítulo \1', content)
    content = re.sub(r"\\ref\{([^}]+)\}", r'\1', content)
    content = re.sub(r"\\cite\{([^}]+)\}", r'[\1]', content)
    content = re.sub(r"\\label\{[^}]*\}", "", content)
    content = re.sub(r"\\vspace\{[^}]*\}", "", content)
    content = content.replace(r"\_", "_")

    # Math inline: $...$
    content = re.sub(r"\$([^$\n]+)\$", r'<span class="inline-math">\1</span>', content)

    # Lists
    # Replace \begin{itemize} ... \end{itemize}
    def replace_list(match, tag="ul"):
        items_raw = match.group(1)
        items = re.split(r"\\item\b", items_raw)
        out = [f"<{tag} class='doc-list'>"]
        for it in items:
            it = it.strip()
            if it:
                out.append(f"<li>{it}</li>")
        out.append(f"</{tag}>")
        return "\n".join(out)

    content = re.sub(r"\\begin\{itemize\}(.*?)\\end\{itemize\}", lambda m: replace_list(m, "ul"), content, flags=re.DOTALL)
    content = re.sub(r"\\begin\{enumerate\}(.*?)\\end\{enumerate\}", lambda m: replace_list(m, "ol"), content, flags=re.DOTALL)

    # Paragraphs: split by double newlines
    raw_paras = content.split("\n\n")
    processed_paras = []
    for p in raw_paras:
        p = p.strip()
        if not p:
            continue
        if p.startswith("<h1") or p.startswith("<h2") or p.startswith("<h3") or p.startswith("<h4") or p.startswith("<ul") or p.startswith("<ol") or p.startswith("__"):
            processed_paras.append(p)
        else:
            # check if it's already a tag
            if p.startswith("<div") or p.startswith("<table"):
                processed_paras.append(p)
            else:
                processed_paras.append(f"<p>{p}</p>")
                
    final_html = "\n\n".join(processed_paras)

    # Restore placeholders
    for idx, cblock in enumerate(code_blocks):
        final_html = final_html.replace(f"__CODE_BLOCK_{idx}__", cblock)
        final_html = final_html.replace(f"<p>__CODE_BLOCK_{idx}__</p>", cblock)
        
    for idx, fblock in enumerate(figure_blocks):
        final_html = final_html.replace(f"__FIGURE_BLOCK_{idx}__", fblock)
        final_html = final_html.replace(f"<p>__FIGURE_BLOCK_{idx}__</p>", fblock)
        
    for idx, tblock in enumerate(table_blocks):
        final_html = final_html.replace(f"__TABLE_BLOCK_{idx}__", tblock)
        final_html = final_html.replace(f"<p>__TABLE_BLOCK_{idx}__</p>", tblock)
        
    for idx, mblock in enumerate(math_blocks):
        final_html = final_html.replace(f"__MATH_BLOCK_{idx}__", mblock)
        final_html = final_html.replace(f"<p>__MATH_BLOCK_{idx}__</p>", mblock)

    return final_html

def build_capitulo7_pdf():
    base_dir = Path("docs/capitulo 7").resolve()
    tex_file = base_dir / "capitulo_7_implementacion.tex"
    output_pdf = base_dir / "capitulo_7_implementacion.pdf"
    docs_pdf = Path("docs/capitulo_7_implementacion.pdf").resolve()
    
    print(f"Leyendo archivo TeX: {tex_file}")
    with open(tex_file, "r", encoding="utf-8") as f:
        tex_content = f.read()
        
    print("Convirtiendo sintaxis LaTeX a HTML estructurado con diagramas en alta resolución...")
    body_html = parse_tex_to_html(tex_content, base_dir)
    
    cover_html = """
    <div class="cover-page">
        <div class="cover-header">
            <div class="institution">UNIVERSIDAD CATÓLICA DE COLOMBIA</div>
            <div class="faculty">FACULTAD DE INGENIERÍA</div>
            <div class="program">PROGRAMA DE INGENIERÍA DE SISTEMAS Y COMPUTACIÓN</div>
        </div>
        
        <div class="cover-body">
            <div class="deliverable-badge">TRABAJO DE GRADO &bull; CAPÍTULO 7</div>
            <h1 class="cover-title">IMPLEMENTACIÓN DE LA PRUEBA DE CONCEPTO (OE4)</h1>
            <h2 class="cover-subtitle">
                Desarrollo en Contenedores Docker, Simulación Empírica con Datos Históricos/Sintéticos, Evaluación Experimental de Reducción de Cuellos de Botella y Validación con Stakeholders en ITY SAS
            </h2>
            <div class="cover-project-box">
                <strong>Enunciado Literal del Objetivo Específico 4 (OE4):</strong><br>
                <em>«Implementar una prueba de concepto de los dos agentes en un entorno de contenedores, ejecutando una simulación con datos históricos o sintéticos, para demostrar la viabilidad técnica y evaluar el potencial de reducción de cuellos de botella.»</em>
            </div>
        </div>
        
        <div class="cover-footer">
            <div class="author-block">
                <strong>Autor:</strong> Alvaro Felipe Lopez Russi &bull; Código: 67000867 &bull; aflopez67@ucatolica.edu.co<br>
                <strong>Director / Asesor de Tesis:</strong> Docente Titular de Grado
            </div>
            <div class="advisor-block">
                <strong>Entidad Colaboradora:</strong> ITY SAS (Bogotá D.C., Colombia)<br>
                <strong>Artefactos Entregados:</strong> 14 Microservicios Docker &bull; LangGraph Supervisor &bull; PostgreSQL/pgvector &bull; RabbitMQ AMQP &bull; Redis Checkpoints &bull; SPA React Backoffice
            </div>
            <div class="cover-date">
                Bogotá D.C., Octubre 2026 &bull; Versión Oficial de Grado
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
        margin: 30px 0;
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
        font-size: 19pt;
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
        line-height: 1.5;
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
    
    .chapter-h1 {
        font-size: 16pt;
        font-weight: 900;
        color: #1e3a8a;
        border-bottom: 2.5px solid #2563eb;
        padding-bottom: 6px;
        margin-top: 28px;
        margin-bottom: 16px;
        page-break-after: avoid;
    }
    
    .section-h2 {
        font-size: 12pt;
        font-weight: 700;
        color: #0f172a;
        border-bottom: 1px solid #cbd5e1;
        padding-bottom: 4px;
        margin-top: 22px;
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
    
    .table-container {
        margin: 14px 0 18px 0;
        page-break-inside: avoid;
    }
    
    .table-caption {
        font-size: 8.5pt;
        font-weight: 600;
        color: #1e3a8a;
        margin-bottom: 5px;
    }
    
    .arch-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 8pt;
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
    
    .figure-container {
        text-align: center;
        margin: 16px 0 20px 0;
        page-break-inside: avoid;
    }
    
    .figure-image {
        max-width: 95%;
        max-height: 520px;
        object-fit: contain;
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
    """
    
    full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Capítulo 7: Implementación de la Prueba de Concepto (OE4)</title>
    <style>{css}</style>
</head>
<body>
    {cover_html}
    {body_html}
</body>
</html>"""
    
    html_file = base_dir / "capitulo_7_temp.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"HTML generado: {html_file}")
    
    print("Iniciando Playwright Chromium para compilar PDF del Capítulo 7...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_file.as_uri(), wait_until="load", timeout=120000)
        
        header_template = """
        <div style="font-size: 6.5pt; color: #64748b; font-family: sans-serif; width: 100%; display: flex; justify-content: space-between; padding: 0 16mm;">
            <span>UNIVERSIDAD CATÓLICA DE COLOMBIA &bull; FACULTAD DE INGENIERÍA</span>
            <span>CAPÍTULO 7: IMPLEMENTACIÓN DE LA PRUEBA DE CONCEPTO (OE4)</span>
        </div>
        """
        
        footer_template = """
        <div style="font-size: 7pt; color: #64748b; font-family: sans-serif; width: 100%; display: flex; justify-content: space-between; padding: 0 16mm;">
            <span>ITY SAS &bull; Sistema Multiagente de Planificación y Publicación (Tesis de Maestría)</span>
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
    print(f"Tamaño del archivo PDF: {size_mb:.2f} MB")
    
    # Copiar también directamente a docs/capitulo_7_implementacion.pdf
    shutil.copyfile(output_pdf, docs_pdf)
    print(f"Copia canónica guardada en: {docs_pdf}")

if __name__ == "__main__":
    build_capitulo7_pdf()
