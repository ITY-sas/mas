import os
import sys
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

def get_base64_image(image_path: Path) -> str:
    if not image_path.exists():
        print(f"Warning: image {image_path} not found")
        return ""
    mime_type = "image/png"
    if image_path.suffix.lower() in (".jpg", ".jpeg"):
        mime_type = "image/jpeg"
    elif image_path.suffix.lower() == ".svg":
        mime_type = "image/svg+xml"
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"

def build_pdf():
    base_dir = Path(__file__).resolve().parent
    diagrams_dir = base_dir / "diagramas"
    output_pdf = base_dir / "manual_ejecucion_poc_multiagente.pdf"
    
    print(f"Building PDF from: {base_dir}")
    print(f"Output target: {output_pdf}")
    
    images = {
        "fig_7_46": get_base64_image(diagrams_dir / "figura_7_46_cumplimiento_oe4.png"),
        "fig_7_06": get_base64_image(diagrams_dir / "figura_7_06_despliegue_contenedores.png"),
        "fig_7_07": get_base64_image(diagrams_dir / "figura_7_07_topologia_red_docker.png"),
        "fig_7_08": get_base64_image(diagrams_dir / "figura_7_08_grafo_supervisor.png"),
        "fig_7_09": get_base64_image(diagrams_dir / "figura_7_09_secuencia_tarea_completa.png"),
        "fig_7_28": get_base64_image(diagrams_dir / "figura_7_28_escenario_1_reparacion.png"),
        "fig_7_29": get_base64_image(diagrams_dir / "figura_7_29_escenario_2_sobrecarga.png"),
        "fig_7_30": get_base64_image(diagrams_dir / "figura_7_30_escenario_3_fallback_llm.png"),
        "fig_7_31": get_base64_image(diagrams_dir / "figura_7_31_escenario_4_recuperacion_amqp.png"),
        "fig_7_32": get_base64_image(diagrams_dir / "figura_7_32_pipeline_metricas.png"),
        "fig_7_34": get_base64_image(diagrams_dir / "figura_7_34_comparacion_tiempo_ciclo.png"),
        "fig_7_35": get_base64_image(diagrams_dir / "figura_7_35_tasa_exito_escenarios.png"),
        "fig_7_45": get_base64_image(diagrams_dir / "figura_7_45_arbol_diagnostico.png"),
        "kpi_1": get_base64_image(diagrams_dir / "kpi_1_tasa_exito_simulacion.png"),
        "kpi_2": get_base64_image(diagrams_dir / "kpi_2_reduccion_tiempo_ciclo.png"),
        "kpi_3": get_base64_image(diagrams_dir / "kpi_3_cobertura_unitarias.png")
    }
    
    # Template without f-string backslash issue
    html_template = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Manual de Ejecución y Validación de la Prueba de Concepto (PoC) - ITY SAS</title>
<!-- KaTeX para renderizado matemático LaTeX perfecto -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function() {
    renderMathInElement(document.body, {
        delimiters: [
            {left: "$$", right: "$$", display: true},
            {left: "$", right: "$", display: false}
        ]
    });
});
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

@page {
    size: A4 portrait;
    margin: 20mm 15mm 20mm 15mm;
    @bottom-right {
        content: counter(page);
    }
}

* {
    box-sizing: border-box;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.55;
    color: #1e293b;
    background-color: #ffffff;
    margin: 0;
    padding: 0;
}

.page-break {
    page-break-before: always;
}

.avoid-break {
    page-break-inside: avoid;
}

/* Portada */
.cover-page {
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 30px 10px 20px 10px;
    box-sizing: border-box;
    page-break-after: always;
}

.cover-header {
    border-bottom: 3px solid #1e3a8a;
    padding-bottom: 15px;
}

.cover-brand {
    font-size: 12pt;
    font-weight: 800;
    letter-spacing: 2px;
    color: #1e3a8a;
    text-transform: uppercase;
}

.cover-doc-type {
    font-size: 10pt;
    color: #64748b;
    font-weight: 500;
    margin-top: 4px;
}

.cover-main {
    margin: auto 0;
}

.cover-title {
    font-size: 26pt;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.2;
    margin-bottom: 12px;
}

.cover-subtitle {
    font-size: 14pt;
    font-weight: 600;
    color: #2563eb;
    line-height: 1.4;
    margin-bottom: 24px;
}

.cover-badge {
    display: inline-block;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #1d4ed8;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 9.5pt;
    font-weight: 600;
    margin-bottom: 25px;
}

.cover-quote-box {
    background-color: #f8fafc;
    border-left: 4px solid #2563eb;
    padding: 16px 20px;
    border-radius: 0 8px 8px 0;
    margin-bottom: 30px;
}

.cover-quote-box p {
    margin: 0;
    font-style: italic;
    color: #334155;
    font-size: 10pt;
    line-height: 1.5;
}

.cover-quote-box strong {
    display: block;
    font-style: normal;
    color: #0f172a;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
}

.cover-metadata-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    background: #f1f5f9;
    padding: 18px 22px;
    border-radius: 8px;
    font-size: 9pt;
}

.cover-metadata-col p {
    margin: 4px 0;
    color: #475569;
}

.cover-metadata-col strong {
    color: #0f172a;
}

.cover-footer {
    border-top: 1px solid #e2e8f0;
    padding-top: 12px;
    display: flex;
    justify-content: space-between;
    font-size: 8.5pt;
    color: #64748b;
}

/* Encabezados */
h1 {
    font-size: 18pt;
    font-weight: 800;
    color: #0f172a;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 6px;
    margin-top: 24pt;
    margin-bottom: 12pt;
    page-break-after: avoid;
}

h1 .sec-num {
    color: #2563eb;
    margin-right: 6px;
}

h2 {
    font-size: 13pt;
    font-weight: 700;
    color: #1e3a8a;
    margin-top: 18pt;
    margin-bottom: 8pt;
    page-break-after: avoid;
}

h2 .sec-num {
    color: #3b82f6;
    margin-right: 5px;
}

h3 {
    font-size: 11pt;
    font-weight: 600;
    color: #334155;
    margin-top: 14pt;
    margin-bottom: 6pt;
    page-break-after: avoid;
}

p {
    margin-top: 0;
    margin-bottom: 8pt;
    text-align: justify;
}

/* Tablas */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 12pt 0;
    font-size: 8.5pt;
    page-break-inside: avoid;
}

th, td {
    padding: 7px 10px;
    text-align: left;
    vertical-align: top;
}

th {
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 700;
    border-top: 1.5px solid #0f172a;
    border-bottom: 1.5px solid #0f172a;
    text-transform: uppercase;
    font-size: 7.5pt;
    letter-spacing: 0.5px;
}

td {
    border-bottom: 1px solid #e2e8f0;
    color: #334155;
}

tr:last-child td {
    border-bottom: 1.5px solid #0f172a;
}

.table-caption {
    font-size: 8.5pt;
    font-weight: 600;
    color: #475569;
    margin-bottom: 4pt;
    text-align: left;
}

/* Código y Listados */
code {
    font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
    font-size: 8.5pt;
    background-color: #f1f5f9;
    color: #0f172a;
    padding: 1.5px 4px;
    border-radius: 4px;
    border: 1px solid #e2e8f0;
}

pre {
    font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
    font-size: 8pt;
    line-height: 1.45;
    background-color: #0f172a;
    color: #f8fafc;
    padding: 12px 14px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 10pt 0;
    page-break-inside: avoid;
}

pre code {
    background: none;
    color: inherit;
    padding: 0;
    border: none;
    font-size: inherit;
}

/* Figuras e Imágenes */
.figure-container {
    margin: 16pt 0;
    text-align: center;
    page-break-inside: avoid;
}

.figure-container img {
    max-width: 95%;
    max-height: 480px;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.figure-caption {
    font-size: 8.5pt;
    color: #475569;
    margin-top: 6pt;
    font-weight: 500;
}

.figure-caption strong {
    color: #0f172a;
}

/* Cajas de Alerta */
.alert-box {
    padding: 12px 16px;
    border-radius: 6px;
    margin: 12pt 0;
    font-size: 9pt;
    page-break-inside: avoid;
}

.alert-info {
    background-color: #eff6ff;
    border-left: 4px solid #3b82f6;
    color: #1e40af;
}

.alert-warning {
    background-color: #fffbeb;
    border-left: 4px solid #f59e0b;
    color: #92400e;
}

.alert-success {
    background-color: #f0fdf4;
    border-left: 4px solid #22c55e;
    color: #166534;
}

.alert-box strong {
    display: block;
    margin-bottom: 3px;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Ecuaciones LaTeX */
.equation-box {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 10pt 0;
    text-align: center;
    page-break-inside: avoid;
}

/* Índice */
.toc-list {
    list-style: none;
    padding-left: 0;
    margin: 15pt 0;
    font-size: 9.5pt;
}

.toc-item {
    margin-bottom: 8pt;
    display: flex;
    justify-content: space-between;
    border-bottom: 1px dotted #cbd5e1;
    padding-bottom: 2pt;
}

.toc-title {
    font-weight: 600;
    color: #1e3a8a;
}

.toc-num {
    color: #64748b;
    font-weight: 500;
}

/* Listas */
ul, ol {
    margin-top: 0;
    margin-bottom: 8pt;
    padding-left: 18pt;
}

li {
    margin-bottom: 4pt;
}
</style>
</head>
<body>

<!-- PORTADA -->
<div class="cover-page">
    <div class="cover-header">
        <div class="cover-brand">ITY SAS &bull; AGENCIA DIGITAL</div>
        <div class="cover-doc-type">Documentación Técnica de Pruebas de Software &bull; Maestría en Ingeniería</div>
    </div>
    
    <div class="cover-main">
        <div class="cover-title">MANUAL DE EJECUCIÓN Y VALIDACIÓN DE LA PRUEBA DE CONCEPTO (PoC)</div>
        <div class="cover-subtitle">Sistema Multi-Agente para la Automatización de Procesos de Ideación y Pre-Producción de Contenido Digital</div>
        
        <div class="cover-badge">EVALUACIÓN EXPERIMENTAL FORMAL &bull; OCTUBRE 2026</div>
        
        <div class="cover-quote-box">
            <strong>Vinculación Formal con el Objetivo Específico 4 (OE4):</strong>
            <p>“Implementar una prueba de concepto de los dos agentes en un entorno de contenedores, ejecutando una simulación con datos históricos o sintéticos, para demostrar la viabilidad técnica y evaluar el potencial de reducción de cuellos de botella.”</p>
        </div>
        
        <div class="cover-metadata-grid">
            <div class="cover-metadata-col">
                <p><strong>Destinatarios:</strong> Desarrolladores e Ingenieros de ITY SAS</p>
                <p><strong>Entorno:</strong> 14 Microservicios Contenerizados (Docker Compose)</p>
                <p><strong>Orquestación:</strong> LangGraph Supervisor (Stateless + Event-Driven)</p>
                <p><strong>Inferencia Local:</strong> Ollama (Gemma 3:4B / Mistral-Nemo)</p>
            </div>
            <div class="cover-metadata-col">
                <p><strong>Dataset de Simulación:</strong> 60 Casos Reales (3 Marcas &times; 2 Formatos)</p>
                <p><strong>KPI 1 (Tasa de Éxito):</strong> 100.0% (Meta: &ge; 90%)</p>
                <p><strong>KPI 2 (Reducción Ciclo):</strong> 99.97% (Meta: &ge; 20%)</p>
                <p><strong>KPI 3 (Cobertura Tests):</strong> 84.0% (Meta: &ge; 80%)</p>
            </div>
        </div>
    </div>
    
    <div class="cover-footer">
        <div>Proyecto de Grado &bull; Sistema Multi-Agente ITY SAS</div>
        <div>Octubre 2026 &bull; Versión 3.0 Final Definitiva</div>
    </div>
</div>

<!-- RESUMEN EJECUTIVO E ÍNDICE -->
<h1>Resumen Ejecutivo y Tabla de Contenido</h1>

<p>Este documento constituye la guía técnica oficial para reproducir, ejecutar, monitorear y validar la Prueba de Concepto (PoC) del sistema multiagente diseñado para la agencia digital <strong>ITY SAS</strong>. La arquitectura desacoplada en 14 microservicios orquestados mediante LangGraph y respaldados en PostgreSQL con pgvector, Redis Stack y RabbitMQ permite superar las limitaciones de escala de los métodos tradicionales de ideación y copywriting.</p>

<div class="alert-box alert-success">
    <strong>Validación Satisfactoria del Objetivo Específico 4 (OE4):</strong>
    La PoC procesó con éxito el 100% de los 60 casos de prueba analizados en tres marcas calibradas (EcoBrand, TechStart y FitLife), reduciendo el tiempo de la Fase 1 de una media manual de 18.83 horas a tan solo 21.44 segundos (reducción de 99.97%), garantizando tolerancia a fallos transitorios y cero fugas multi-inquilino.
</div>

<h2>Estructura del Manual</h2>
<div class="toc-list">
    <div class="toc-item"><span class="toc-title">1. Vinculación Formal con el Objetivo Específico 4 (OE4)</span><span class="toc-num">Pág. 3</span></div>
    <div class="toc-item"><span class="toc-title">2. Requisitos Técnicos y Arquitectura del Entorno</span><span class="toc-num">Pág. 5</span></div>
    <div class="toc-item"><span class="toc-title">3. Guía de Comandos: Construcción, Despliegue y Operación</span><span class="toc-num">Pág. 8</span></div>
    <div class="toc-item"><span class="toc-title">4. Descripción Exhaustiva de los Escenarios de Simulación</span><span class="toc-num">Pág. 11</span></div>
    <div class="toc-item"><span class="toc-title">5. Interpretación y Auditoría de Logs Distribuidos</span><span class="toc-num">Pág. 15</span></div>
    <div class="toc-item"><span class="toc-title">6. Extracción y Evaluación Formal de Métricas (LaTeX y Scripts)</span><span class="toc-num">Pág. 18</span></div>
    <div class="toc-item"><span class="toc-title">7. Árbol de Decisión y Diagnóstico de Incidencias (Troubleshooting)</span><span class="toc-num">Pág. 22</span></div>
    <div class="toc-item"><span class="toc-title">8. Conclusiones y Recomendaciones para Futuros Desarrolladores</span><span class="toc-num">Pág. 24</span></div>
</div>

<div class="figure-container">
    <img src="IMAGE_FIG_7_46" alt="Cumplimiento del OE4">
    <div class="figure-caption"><strong>Figura 1:</strong> Trazabilidad y correspondencia del Objetivo Específico 4 (OE4): Compromiso vs. Entrega.</div>
</div>

<div class="page-break"></div>

<!-- SECCIÓN 1: VINCULACIÓN CON OE4 -->
<h1><span class="sec-num">1.</span> Vinculación Formal con el Objetivo Específico 4 (OE4)</h1>

<h2>1.1. Declaración Literal y Alcance del OE4</h2>
<p>El marco metodológico de la investigación establece para el <strong>Objetivo Específico 4 (OE4)</strong> el siguiente enunciado contractual:</p>

<div class="cover-quote-box">
    <strong>Enunciado Literal del OE4:</strong>
    <p>“Implementar una prueba de concepto de los dos agentes en un entorno de contenedores, ejecutando una simulación con datos históricos o sintéticos, para demostrar la viabilidad técnica y evaluar el potencial de reducción de cuellos de botella.”</p>
</div>

<p>Para satisfacer sin ambigüedades este objetivo, la Prueba de Concepto aborda cuatro dimensiones operativas:</p>
<ul>
    <li><strong>Implementación real de dos agentes de software:</strong> El <code>agente-ideacion</code> (encargado de investigar tendencias, recuperar directrices de marca y generar el dossier estructurado en formato Reel o Post) y el <code>agente-publicacion</code> (encargado de redactar copys adaptados por red social y gestionar la entrega mediante compuerta humana).</li>
    <li><strong>Entorno de contenedores reproducible:</strong> Un stack orquestado mediante Docker Compose integrado por 14 microservicios independientes, garantizando portabilidad e independencia de infraestructura.</li>
    <li><strong>Simulación basada en datos reales y sintéticos:</strong> Ejecución de una campaña estadística de 60 casos reales representativos de tres nichos económicos (sostenibilidad, fintech y fitness), confrontados con un registro histórico de 166 piezas producidas manualmente en ITY SAS.</li>
    <li><strong>Demostración de viabilidad técnica y mitigación de cuellos de botella:</strong> Medición cuantitativa del tiempo de ciclo, la tasa de éxito bajo estrés y la cobertura de pruebas unitarias.</li>
</ul>

<h2>1.2. Contexto de ITY SAS y Cuellos de Botella del Diagnóstico (OE1)</h2>
<p>Durante la ejecución del <strong>Objetivo Específico 1 (OE1)</strong>, se recopilaron datos del proceso tradicional humano en la agencia digital <strong>ITY SAS</strong> (archivo <code>docs/resultado_pruebas/linea_base_manual_ity_sas.csv</code>). El análisis descriptivo de 166 contenidos permitió categorizar tres restricciones críticas (cuellos de botella):</p>

<table>
    <div class="table-caption">Tabla 1: Diagnóstico de criticidad de cuellos de botella en la línea base de ITY SAS (OE1).</div>
    <thead>
        <tr>
            <th>Código</th>
            <th>Cuello de Botella Detectado</th>
            <th>Índice Criticidad (IC)</th>
            <th>Impacto Operativo Histórico</th>
            <th>Mecanismo Técnico de Mitigación en la PoC</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>R1</strong></td>
            <td>Retrabajo editorial por desalineación con la marca</td>
            <td><strong>15 / 15 (Máximo)</strong></td>
            <td>42.5% de las piezas requerían re-edición y múltiples rondas de aprobación humana por copys genéricos o estructuras visuales rotas.</td>
            <td>Inferencia RAG multicanal sobre <code>brand_knowledge</code> con pgvector y bucle de auto-reparación estructurada Pydantic.</td>
        </tr>
        <tr>
            <td><strong>R2</strong></td>
            <td>Lentitud operativa extrema en la Fase 1 (Ideación y Brief)</td>
            <td><strong>14 / 15 (Alto)</strong></td>
            <td>Media de 18.83 horas netas (1,129.8 min) dedicadas a investigación manual de tendencias y formulación de guiones/dossiers.</td>
            <td>Automatización distribuida en LangGraph desacoplada vía colas RabbitMQ, reduciendo la fase creativa a menos de 25 segundos.</td>
        </tr>
        <tr>
            <td><strong>R3</strong></td>
            <td>Dispersión e ineficiencia en adaptación multicanal</td>
            <td><strong>12 / 15 (Moderado)</strong></td>
            <td>Tiempo de ciclo total de 93.05 horas (3.88 días) debido a la fricción de adaptar el copy a Instagram, LinkedIn o Facebook manualmente.</td>
            <td>Agente publicador especializado con redacción multiformato simultánea y entrega desacoplada mediante API de Postiz.</td>
        </tr>
    </tbody>
</table>

<h2>1.3. Matriz de Cumplimiento de los Tres KPIs de la Tesis</h2>
<p>El rendimiento empírico de la PoC fue evaluado contra los tres Indicadores Clave de Rendimiento (KPIs) definidos para el OE4. Como se aprecia en la Tabla 2, todos los indicadores superaron el umbral contractual esperado.</p>

<table>
    <div class="table-caption">Tabla 2: Matriz contractual de KPIs del Objetivo Específico 4 (OE4).</div>
    <thead>
        <tr>
            <th>KPI</th>
            <th>Descripción y Fórmula</th>
            <th>Deficiente</th>
            <th>Aceptable</th>
            <th>Esperado</th>
            <th>Resultado Obtenido</th>
            <th>Veredicto</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>KPI 1</strong></td>
            <td><strong>Tasa de éxito en simulación ($S_r$):</strong> Proporción de briefs completados sin abortos de proceso ni excepciones no controladas.</td>
            <td>&lt; 70%</td>
            <td>70% - 89%</td>
            <td>&ge; 90%</td>
            <td><strong>100.0%</strong><br>(60/60 briefs)</td>
            <td><strong>SUPERADO (Nivel Esperado)</strong></td>
        </tr>
        <tr>
            <td><strong>KPI 2</strong></td>
            <td><strong>Reducción de tiempo de ciclo ($\Delta T_{\%}$):</strong> Disminución porcentual del tiempo de ideación frente a la media manual de 18.83 horas.</td>
            <td>&lt; 10%</td>
            <td>10% - 19%</td>
            <td>&ge; 20%</td>
            <td><strong>99.97%</strong><br>(21.44 s en Fase 1)</td>
            <td><strong>SUPERADO (Nivel Esperado)</strong></td>
        </tr>
        <tr>
            <td><strong>KPI 3</strong></td>
            <td><strong>Cobertura de pruebas unitarias ($C_u$):</strong> Cobertura de sentencias de código ejecutable sobre los agentes lógicos.</td>
            <td>&lt; 60%</td>
            <td>60% - 79%</td>
            <td>&ge; 80%</td>
            <td><strong>84.0%</strong><br>(397/475 sentencias)</td>
            <td><strong>SUPERADO (Nivel Esperado)</strong></td>
        </tr>
    </tbody>
</table>

<div class="page-break"></div>

<!-- SECCIÓN 2: REQUISITOS TÉCNICOS Y ARQUITECTURA -->
<h1><span class="sec-num">2.</span> Requisitos Técnicos y Arquitectura del Entorno</h1>

<h2>2.1. Especificaciones de Hardware y Plataforma</h2>
<p>Para asegurar una ejecución determinista de la PoC sin retrasos ocasionados por contención de recursos, la estación de trabajo debe satisfacer los siguientes requerimientos:</p>

<ul>
    <li><strong>Unidad Central de Procesamiento (CPU):</strong> Procesador de 64 bits con arquitectura x86_64 o ARM64, mínimo 4 núcleos físicos y 8 hilos de ejecución (Intel Core i5 de 10ª generación, AMD Ryzen 5 3600, Apple Silicon M1 o superior).</li>
    <li><strong>Memoria de Acceso Aleatorio (RAM):</strong> Mínimo 16 GB de RAM física instalada. Es imperativo asignar al menos <strong>8 GB de memoria dedicada</strong> al subsistema de contenedores Docker Desktop / WSL2 en el archivo <code>.wslconfig</code>.</li>
    <li><strong>Almacenamiento:</strong> Mínimo 25 GB de espacio libre en unidad de estado sólido (SSD NVMe recomendado). Los modelos LLM de Ollama ocupan aproximadamente 10 GB y las imágenes base de Docker 8 GB.</li>
    <li><strong>Entorno Operativo:</strong> Microsoft Windows 10/11 (con subsistema WSL2 actualizado), Linux Ubuntu 22.04 LTS o macOS Ventura 13.0+.</li>
    <li><strong>Puertos de Red Requeridos en el Anfitrión:</strong> Asegurar la disponibilidad de los puertos <code>5432</code> (PostgreSQL), <code>6379</code> (Redis), <code>5672</code>/<code>15672</code> (RabbitMQ), <code>8000</code> a <code>8016</code> (Microservicios y Agentes), <code>11434</code> (Ollama), <code>4007</code> (Postiz) y <code>3001</code> (Studio Frontend).</li>
</ul>

<h2>2.2. Ecosistema de 14 Microservicios Contenerizados</h2>
<p>La arquitectura del sistema multi-agente está dividida en cuatro capas desacopladas mediante el bus de eventos AMQP y almacenamiento distribuido:</p>

<div class="figure-container">
    <img src="IMAGE_FIG_7_06" alt="Despliegue de Contenedores">
    <div class="figure-caption"><strong>Figura 2:</strong> Diagrama de despliegue en contenedores Docker de la PoC multi-agente.</div>
</div>

<div class="figure-container">
    <img src="IMAGE_FIG_7_07" alt="Topología de Red Docker">
    <div class="figure-caption"><strong>Figura 3:</strong> Topología de red interna Docker: Aislamiento y comunicación bidireccional.</div>
</div>

<table>
    <div class="table-caption">Tabla 3: Inventario maestro de contenedores, puertos y responsabilidades técnicas.</div>
    <thead>
        <tr>
            <th>Contenedor</th>
            <th>Puerto Host</th>
            <th>Imagen Base</th>
            <th>Función en la Arquitectura</th>
        </tr>
    </thead>
    <tbody>
        <tr><td><code>rabbitmq</code></td><td>5672, 15672</td><td>rabbitmq:3-management</td><td>Broker AMQP para distribución asíncrona de eventos de tareas.</td></tr>
        <tr><td><code>postgres</code></td><td>5432</td><td>pgvector/pgvector:pg16</td><td>Base de datos relacional y vectorial. Embeddings con índice HNSW.</td></tr>
        <tr><td><code>redis</code></td><td>6379</td><td>redis/redis-stack-server:7.4.0-v3</td><td>TaskStore central, checkpoints LangGraph y caché de LLM Gateway.</td></tr>
        <tr><td><code>llm-gateway</code></td><td>8003</td><td>python:3.10-slim (custom)</td><td>Enrutamiento inteligente, reintentos con backoff y fallback automático.</td></tr>
        <tr><td><code>tool-client</code></td><td>8010</td><td>python:3.10-slim (custom)</td><td>Extracción de perfiles de clientes, pilares de marca y restricciones.</td></tr>
        <tr><td><code>tool-trends</code></td><td>8011</td><td>python:3.10-slim (custom)</td><td>Análisis de tendencias de mercado y palabras clave emergentes.</td></tr>
        <tr><td><code>tool-competitors</code></td><td>8012</td><td>python:3.10-slim (custom)</td><td>Recuperación de piezas de competidores para evitar redundancia.</td></tr>
        <tr><td><code>tool-rag</code></td><td>8013</td><td>python:3.10-slim (custom)</td><td>Búsqueda semántica aislada por <code>brand_id</code> sobre <code>brand_knowledge</code>.</td></tr>
        <tr><td><code>tool-news</code></td><td>8014</td><td>python:3.10-slim (custom)</td><td>Consulta de novedades de la industria para alineación noticiosa.</td></tr>
        <tr><td><code>tool-trending</code></td><td>8015</td><td>python:3.10-slim (custom)</td><td>Identificación de audios, retos y formatos virales en redes sociales.</td></tr>
        <tr><td><code>tool-postiz</code></td><td>8016</td><td>python:3.10-slim (custom)</td><td>Adaptador hacia Postiz API para catálogo de canales y envíos.</td></tr>
        <tr><td><code>agente-ideacion</code></td><td>8000</td><td>python:3.10-slim (custom)</td><td>Worker LangGraph para ideación y dossier con auto-reparación Pydantic.</td></tr>
        <tr><td><code>agente-publicacion</code></td><td>8001</td><td>python:3.10-slim (custom)</td><td>Worker LangGraph para redacción multicanal y adaptación editorial.</td></tr>
        <tr><td><code>orchestrator</code></td><td>8002</td><td>python:3.10-slim (custom)</td><td>Supervisor LangGraph stateless con <code>interrupt()</code> y <code>resume</code>.</td></tr>
    </tbody>
</table>

<h2>2.3. Gestión de Secretos y Variables de Entorno (<code>.env</code>)</h2>
<p>El sistema se parametriza en tiempo de ejecución a través de un archivo <code>.env</code> ubicado en la raíz del repositorio. No versione contraseñas ni claves API en repositorios públicos.</p>

<pre><code># --- Configuracion de Modelos Locales en Ollama ---
OLLAMA_MODEL=gemma3:4b
EMBEDDING_MODEL=nomic-embed-text
LLM_FALLBACK_MODEL=mistral-nemo

# --- Integracion con Postiz (Local) ---
POSTIZ_API_URL=http://host.docker.internal:4007/api/public/v1
POSTIZ_API_KEY=tu_api_key_extraida_de_postiz_settings

# --- Credenciales OAuth de Plataformas Sociales (Opcional) ---
LINKEDIN_CLIENT_ID=tu_linkedin_client_id
LINKEDIN_CLIENT_SECRET=tu_linkedin_client_secret</code></pre>

<div class="page-break"></div>

<!-- SECCIÓN 3: GUÍA DE COMANDOS -->
<h1><span class="sec-num">3.</span> Guía de Comandos: Construcción, Despliegue y Operación</h1>

<p>Para levantar la Prueba de Concepto desde cero de manera idéntica a las pruebas certificadas en este informe, siga la secuencia estructurada de comandos en su terminal (PowerShell en Windows o Bash en Linux):</p>

<h2>3.1. Fase 1: Descarga y Preparación de Modelos en Ollama</h2>
<p>Ollama debe estar corriendo en el sistema anfitrión escuchando en <code>localhost:11434</code>:</p>

<pre><code># Descargar el modelo primario de generacion creativa (Gemma 3 de 4B parametros)
ollama pull gemma3:4b

# Descargar el modelo secundario de respaldo / contingencia (Mistral NeMo 12B)
ollama pull mistral-nemo

# Descargar el modelo denso de representacion vectorial (768 dimensiones)
ollama pull nomic-embed-text

# Verificar que los 3 modelos se encuentren cargados en el inventario local
ollama list</code></pre>

<h2>3.2. Fase 2: Arranque de Postiz (Plataforma Desacoplada de Redes)</h2>
<pre><code># Desplazar a la carpeta de configuracion de Postiz
cd postiz/postiz-docker-compose

# Levantar Postiz y su base interna
docker compose up -d

# Retornar a la raiz del repositorio
cd ../..</code></pre>

<div class="alert-box alert-info">
    <strong>Configuración Inicial de Postiz:</strong>
    Abra su navegador en <code>http://localhost:4007</code>, cree su usuario administrativo y conecte el canal deseado (LinkedIn / Instagram) en la sección <em>Channels / Integrations</em>. Posteriormente, diríjase a <em>Settings &rarr; API Keys</em>, genere una clave y colóquela en el parámetro <code>POSTIZ_API_KEY</code> de su archivo <code>.env</code>.
</div>

<h2>3.3. Fase 3: Construcción y Encendido de los 14 Microservicios</h2>
<pre><code># Validar la sintaxis y sustitucion de variables de Docker Compose
docker compose config --quiet

# Construir imagenes personalizadas y encender los contenedores en segundo plano
docker compose up -d --build

# Verificar que los 14 contenedores esten en estado "Up" o "healthy"
docker compose ps</code></pre>

<h2>3.4. Fase 4: Verificación Integral de Salud (Healthchecks)</h2>
<p>Valide que todos los componentes centrales estén operando y comunicándose adecuadamente:</p>

<pre><code># Consultar salud del orquestador supervisor
curl -s http://localhost:8002/health | jq .

# Consultar salud del Agente de Ideacion y del Agente de Publicacion
curl -s http://localhost:8000/health
curl -s http://localhost:8001/health

# Consultar conectividad del LLM Gateway hacia Ollama
curl -s http://localhost:8003/health

# Consultar configuracion de Postiz Tool
curl -s http://localhost:8016/health</code></pre>

<div class="alert-box alert-warning">
    <strong>Respuesta Esperada en Orquestador:</strong>
    El endpoint <code>/health</code> del orquestador debe devolver <code>status: ok</code> y reportar los subsistemas <code>postgres</code>, <code>redis</code>, <code>rabbitmq</code> y <code>gateway</code> con valor <code>ok</code>.
</div>

<h2>3.5. Fase 5: Aplicación de Migraciones en Volumen Existente</h2>
<p>Si los volúmenes de PostgreSQL ya existían previamente en Docker, aplique manualmente los scripts DDL para incorporar las tablas de batches y canales:</p>

<pre><code>docker compose exec -T postgres psql -U postgres -d ideation_db -f - < migrations/001_multi_tenant_foundation.sql
docker compose exec -T postgres psql -U postgres -d ideation_db -f - < migrations/002_brand_knowledge_and_channels.sql
docker compose exec -T postgres psql -U postgres -d ideation_db -f - < migrations/003_publication_platform.sql
docker compose exec -T postgres psql -U postgres -d ideation_db -f - < migrations/004_idea_generation_batches.sql
docker compose exec -T postgres psql -U postgres -d ideation_db -f - < migrations/005_brand_scoped_idea_batches.sql
docker compose exec -T postgres psql -U postgres -d ideation_db -f - < migrations/006_crud_and_lifecycle_states.sql</code></pre>

<h2>3.6. Fase 6: Carga de Datos Semilla (Seed Data)</h2>
<p>Pueble la base de datos con las tres marcas calibradas para la prueba (EcoBrand, TechStart, FitLife) y sus bases de conocimiento vectorial asociadas:</p>

<pre><code>python seed_data.py</code></pre>

<h2>3.7. Fase 7: Ejecución de Suites de Pruebas Automatizadas</h2>
<pre><code># 1. Pruebas unitarias de agentes con reporte detallado de cobertura (KPI 3)
pytest tests/unit -v --cov=agente_ideacion --cov=agente_publicacion

# 2. Pruebas de integracion entre microservicios
pytest tests/integration -v

# 3. Prueba integral de ciclo completo E2E
python prueba_e2e.py</code></pre>

<h2>3.8. Fase 8: Arranque de Studio (Frontend Interactivo)</h2>
<pre><code># Instalar paquetes requeridos por el BFF
python -m pip install -r frontend/requirements.txt

# Iniciar servidor FastAPI/Uvicorn para la interfaz web en puerto 3001
python -m uvicorn frontend.server:app --host 127.0.0.1 --port 3001</code></pre>
<p>Abra <code>http://127.0.0.1:3001</code> en su navegador para interactuar con la consola de generación de ideas, seguimiento de tareas y aprobación humana de publicaciones.</p>

<h2>3.9. Fase 9: Procedimiento de Parada Limpia (Stop vs. Down)</h2>
<div class="alert-box alert-warning">
    <strong>¡PRECAUCIÓN CON LOS VOLÚMENES PERSISTENTES!</strong>
    Para apagar el entorno conservando intactos todos los registros de simulación, la base de datos PostgreSQL y los checkpoints de Redis, ejecute:
    <pre><code>docker compose stop</code></pre>
    <strong>NUNCA</strong> ejecute <code>docker compose down -v</code> a menos que intencionalmente desee purgar y destruir la totalidad de los datos persistentes de la base de datos.
</div>

<div class="page-break"></div>

<!-- SECCIÓN 4: ESCENARIOS DE SIMULACIÓN -->
<h1><span class="sec-num">4.</span> Descripción Exhaustiva de los Escenarios de Simulación</h1>

<p>Para someter la arquitectura a pruebas de estrés rigurosas, se implementaron cinco escenarios empíricos que aíslan variables de fallo y sobrecarga operativa:</p>

<h2>4.1. Escenario 1 (E1): Brief Incompleto y Auto-reparación Estructurada</h2>
<p><strong>Objetivo:</strong> Mitigar el cuello de botella <strong>R1</strong> (retrabajo editorial). Evalúa la capacidad del sistema para asimilar briefs con omisiones severas de información técnica y corregir desviaciones del esquema JSON sin intervención humana.</p>

<div class="figure-container">
    <img src="IMAGE_FIG_7_28" alt="Escenario 1 Reparacion">
    <div class="figure-caption"><strong>Figura 4:</strong> Secuencia del Escenario 1: Ingesta de brief incompleto y auto-reparación estructurada.</div>
</div>

<p><strong>Mecanismo Técnico:</strong></p>
<ol>
    <li>El cliente envía un brief con información deliberadamente ambigua o incompleta (ej. <em>"crear un reel de protector solar"</em>, omitiendo duración, llamados a la acción y escenas).</li>
    <li>El nodo <code>retrieve_context</code> consulta a <code>tool-client</code> y <code>tool-rag</code> para inferir el tono de la marca y las restricciones vigentes.</li>
    <li>El nodo <code>generate_dossier</code> genera una primera respuesta JSON. Si el LLM omite propiedades requeridas por el esquema Pydantic (como <code>visual_description</code> o <code>audio_script</code>), el validador captura la excepción <code>ValidationError</code>.</li>
    <li>En lugar de abortar la tarea, el grafo activa una arista condicional hacia <code>self_repair</code>, inyectando el detalle del error en el prompt y forzando una segunda pasada.</li>
    <li>El agente corrige el dossier en una pasada ($100\%$ de éxito en la prueba), produciendo un esquema conforme a <code>DossierReelOutput</code>.</li>
</ol>

<h2>4.2. Escenario 2 (E2): Sobrecarga Concurrente de Tareas (Carga AMQP)</h2>
<p><strong>Objetivo:</strong> Mitigar el cuello de botella <strong>R2</strong> (lentitud por acumulación de trabajo). Comprobar que una ráfaga simultánea de requerimientos creativos no bloquee el sistema ni provoque pérdida de información.</p>

<div class="figure-container">
    <img src="IMAGE_FIG_7_29" alt="Escenario 2 Sobrecarga">
    <div class="figure-caption"><strong>Figura 5:</strong> Secuencia del Escenario 2: Procesamiento concurrente desacoplado bajo sobrecarga.</div>
</div>

<p><strong>Mecanismo Técnico:</strong></p>
<ol>
    <li>Se inyectó una ráfaga de 15 peticiones concurrentes mediante llamadas a la API del orquestador (<code>POST /process?wait=false</code>).</li>
    <li>El orquestador genera de inmediato un <code>task_id</code> único, almacena los metadatos en el <code>TaskStore</code> de Redis con estado <code>"queued"</code> y publica el mensaje en RabbitMQ (<code>ideation_queue</code>).</li>
    <li>Los workers del <code>agente-ideacion</code> consumen los mensajes de forma regulada aplicando mecanismos de contrapresión (<em>backpressure</em>).</li>
    <li>Cada tarea avanza independientemente sin interferir con las demás. No se registró ninguna pérdida de mensajes ni saturación de memoria RAM.</li>
</ol>

<h2>4.3. Escenario 3 (E3): Fallo y Fallback Automático en LLM Gateway</h2>
<p><strong>Objetivo:</strong> Evaluar la resiliencia del sistema ante interrupciones no programadas o latencias extremas en el proveedor de inferencia principal.</p>

<div class="figure-container">
    <img src="IMAGE_FIG_7_30" alt="Escenario 3 Fallback LLM">
    <div class="figure-caption"><strong>Figura 6:</strong> Diagrama de estados del Escenario 3: Conmutación por contingencia en el LLM Gateway.</div>
</div>

<p><strong>Mecanismo Técnico:</strong></p>
<ol>
    <li>Se indujo un fallo artificial en el modelo primario <code>gemma3:4b</code> desconectando su endpoint o emulando respuestas HTTP 500.</li>
    <li>El <code>llm-gateway</code> interceptó el error de conexión, aplicó una política de reintentos con retroceso exponencial (<em>exponential backoff</em>) y, tras agotar dos reintentos, activó el circuito de contingencia.</li>
    <li>El gateway conmutó la inferencia hacia el modelo de respaldo <code>mistral-nemo</code>, preservando el mismo esquema de salida estructurada JSON.</li>
    <li>La tarea se completó sin que el orquestador ni el cliente experimentaran errores fatales.</li>
</ol>

<h2>4.4. Escenario 4 (E4): Caída Forzada de Broker RabbitMQ y Recuperación</h2>
<p><strong>Objetivo:</strong> Verificar la capacidad de recuperación ante desastres y la preservación de estado mediante checkpoints externos en Redis Stack.</p>

<div class="figure-container">
    <img src="IMAGE_FIG_7_31" alt="Escenario 4 Recuperacion AMQP">
    <div class="figure-caption"><strong>Figura 7:</strong> Secuencia del Escenario 4: Recuperación de tareas tras la caída forzada de RabbitMQ.</div>
</div>

<p><strong>Mecanismo Técnico:</strong></p>
<ol>
    <li>Durante la ejecución de una tarea activa en LangGraph, se forzó la detención abrupta del contenedor de mensajería ejecutando <code>docker stop rabbitmq</code>.</li>
    <li>Los microservicios conservaron el estado en Redis Stack mediante <code>langgraph-checkpoint-redis</code>.</li>
    <li>Al reiniciar el contenedor (<code>docker start rabbitmq</code>), los agentes detectaron el restablecimiento de la conexión, reanudaron el consumo y recuperaron el checkpoint exacto donde ocurrió la interrupción, completando la tarea exitosamente.</li>
</ol>

<h2>4.5. Escenario 5 (E5): Aislamiento Multi-Tenant Estricto en pgvector</h2>
<p><strong>Objetivo:</strong> Mitigar el riesgo de fuga de información de marca o mezclas de contexto editorial entre clientes de ITY SAS.</p>
<p><strong>Mecanismo Técnico:</strong> Se inyectaron 60 consultas de búsqueda vectorial semántica con el mismo término de búsqueda (ej. <em>"planes de suscripción"</em>) alternando <code>brand_id=1</code> (EcoBrand) y <code>brand_id=2</code> (TechStart). Se comprobó mediante aserciones automatizadas que el <strong>100% de los fragmentos recuperados</strong> pertenecían exclusivamente al inquilino correspondiente, logrando una tasa de contaminación cruzada de <strong>0.0%</strong>.</p>

<div class="page-break"></div>

<!-- SECCIÓN 5: INTERPRETACIÓN Y AUDITORÍA DE LOGS -->
<h1><span class="sec-num">5.</span> Interpretación y Auditoría de Logs Distribuidos</h1>

<h2>5.1. Estructura Estándar de Logs JSON</h2>
<p>Cada microservicio está instrumentado con un formateador de logs estructurados en JSON. La Figura 8 ilustra el pipeline de ingesta y análisis de eventos.</p>

<div class="figure-container">
    <img src="IMAGE_FIG_7_32" alt="Pipeline Metricas">
    <div class="figure-caption"><strong>Figura 8:</strong> Pipeline de instrumentación, extracción y procesamiento analítico de logs estructurados.</div>
</div>

<p>A continuación se detalla una entrada de log real capturada durante la ejecución de una tarea en el Agente de Ideación:</p>

<pre><code>{
  "timestamp": "2026-10-14T20:15:32.412850Z",
  "level": "INFO",
  "service": "agente-ideacion",
  "task_id": "task_8f3a1b02-4c91-4d7e-9a12-88f1c34a2e5d",
  "correlation_id": "amqp_corr_3b9942a1",
  "brand_id": 1,
  "node": "generate_dossier",
  "state_status": "in_progress",
  "llm_provider": "ollama",
  "llm_model": "gemma3:4b",
  "duration_ms": 14250.4,
  "event": "dossier_generated_successfully",
  "details": {
    "format": "reel",
    "scenes_count": 4,
    "self_repair_loops": 0
  }
}</code></pre>

<h2>5.2. Trazabilidad de Estados con Correlation ID (<code>task_id</code>)</h2>
<p>El identificador <code>task_id</code> generado por el orquestador acompaña la petición a lo largo de todos los contenedores y colas AMQP. Las Figuras 9 y 10 ilustran el grafo LangGraph del supervisor y la secuencia completa de estados de una tarea.</p>

<div class="figure-container">
    <img src="IMAGE_FIG_7_08" alt="Grafo Supervisor">
    <div class="figure-caption"><strong>Figura 9:</strong> Grafo de estados del Supervisor (Orquestador): Interrupción (HITL) y reanudación.</div>
</div>

<div class="figure-container">
    <img src="IMAGE_FIG_7_09" alt="Secuencia Tarea Completa">
    <div class="figure-caption"><strong>Figura 10:</strong> Diagrama de secuencia de una tarea completa desde el brief hasta la entrega social.</div>
</div>

<h2>5.3. Guía Práctica de Filtrado de Logs en Tiempo Real</h2>
<pre><code># 1. Monitorear logs de un servicio en tiempo real
docker compose logs -f orchestrator

# 2. Filtrar logs de una tarea especifica en todos los contenedores
docker compose logs | grep "task_8f3a1b02"

# 3. Filtrar unicamente advertencias y errores criticos
docker compose logs --tail 200 | grep -E "ERROR|WARN"

# 4. Inspeccionar las llamadas al LLM Gateway en busca de fallbacks activados
docker compose logs llm-gateway | grep "fallback_triggered"</code></pre>

<div class="page-break"></div>

<!-- SECCIÓN 6: EXTRACCIÓN Y EVALUACIÓN DE MÉTRICAS -->
<h1><span class="sec-num">6.</span> Extracción y Evaluación Formal de Métricas (LaTeX y Scripts)</h1>

<h2>6.1. Formulación Matemática de los Modelos de Medición</h2>

<div class="equation-box">
    <strong>1. Tiempo de Ciclo Total ($T_c$) y Fase 1 ($T_{\text{fase1}}$):</strong>
    $$T_c = T_{\text{ingesta}} + T_{\text{ideación}} + T_{\text{espera\_humana}} + T_{\text{publicación}} + T_{\text{entrega}}$$
    $$T_{\text{fase1, PoC}} = T_{\text{ingesta}} + T_{\text{contexto\_RAG}} + T_{\text{generación\_LLM}} + T_{\text{auto\_reparación}}$$
</div>

<div class="equation-box">
    <strong>2. Porcentaje de Reducción de Tiempo de Ciclo ($\Delta T_{\%}$):</strong>
    $$\Delta T_{\%} = \\left( \\frac{T_{\\text{manual}} - T_{\\text{PoC}}}{T_{\\text{manual}}} \\right) \\times 100\\%$$
</div>

<div class="equation-box">
    <strong>3. Tasa de Éxito en Simulación ($S_r$):</strong>
    $$S_r = \\left( \\frac{1}{N} \\sum_{i=1}^{N} \\mathbb{I}(\\text{estado}_i = \\text{completed}) \\right) \\times 100\\%$$
</div>

<div class="equation-box">
    <strong>4. Cobertura de Pruebas Unitarias ($C_u$):</strong>
    $$C_u = \\left( \\frac{S_{\\text{ejecutadas}}}{S_{\\text{totales}}} \\right) \\times 100\\% = \\frac{397}{475} \\times 100\\% = 84.0\\%$$
</div>

<div class="equation-box">
    <strong>5. Índice Ponderado de Automatización del Proceso ($I_A$):</strong>
    $$I_A = \\frac{\\sum_{j=1}^{5} w_j \\cdot \\alpha_j}{\\sum_{j=1}^{5} w_j} = 0.84 \\quad (84\\%)$$
</div>

<h2>6.2. Resultados Empíricos Consolidados de la Simulación ($N=60$)</h2>
<p>La evaluación empírica formal se ejecutó sobre 60 casos de prueba distribuidos balanceadamente entre las tres marcas calibradas:</p>

<table>
    <div class="table-caption">Tabla 4: Rendimiento empírico de la PoC por marca y formato (Campaña real N=60).</div>
    <thead>
        <tr>
            <th>Marca de Prueba</th>
            <th>Muestras</th>
            <th>Tasa Éxito</th>
            <th>Media Ideación</th>
            <th>Media Publicación</th>
            <th>Tiempo Total PoC</th>
            <th>Reducción vs. Manual</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>EcoBrand (ID 1)</strong></td>
            <td>20 casos</td>
            <td><strong>100.0%</strong></td>
            <td>27.05 s</td>
            <td>7.67 s</td>
            <td><strong>34.72 s (0.58 min)</strong></td>
            <td><strong>99.96%</strong></td>
        </tr>
        <tr>
            <td><strong>TechStart (ID 2)</strong></td>
            <td>20 casos</td>
            <td><strong>100.0%</strong></td>
            <td>19.48 s</td>
            <td>4.41 s</td>
            <td><strong>23.89 s (0.40 min)</strong></td>
            <td><strong>99.97%</strong></td>
        </tr>
        <tr>
            <td><strong>FitLife (ID 3)</strong></td>
            <td>20 casos</td>
            <td><strong>100.0%</strong></td>
            <td>21.20 s</td>
            <td>4.94 s</td>
            <td><strong>26.14 s (0.44 min)</strong></td>
            <td><strong>99.96%</strong></td>
        </tr>
        <tr>
            <td><strong>CONSOLIDADO GLOBAL</strong></td>
            <td><strong>60 casos</strong></td>
            <td><strong>100.0%</strong></td>
            <td><strong>21.44 s</strong></td>
            <td><strong>5.46 s</strong></td>
            <td><strong>26.90 s (0.45 min)</strong></td>
            <td><strong>99.97%</strong></td>
        </tr>
    </tbody>
</table>

<div class="figure-container">
    <img src="IMAGE_FIG_7_34" alt="Comparacion Tiempo Ciclo">
    <div class="figure-caption"><strong>Figura 11:</strong> Reducción drástica del tiempo de ciclo en escala logarítmica (Manual vs. PoC Multi-Agente).</div>
</div>

<div class="figure-container">
    <img src="IMAGE_FIG_7_35" alt="Tasa Exito Escenarios">
    <div class="figure-caption"><strong>Figura 12:</strong> Tasa de éxito alcanzada en cada escenario de estrés (100% de efectividad).</div>
</div>

<h2>6.3. Scripts de Reproducción de Métricas y Consultas SQL</h2>
<p>Para recalcular las métricas y regenerar las figuras estadísticas:</p>

<pre><code># 1. Ejecutar campana completa de simulacion
python docs/resultado_pruebas/ejecutar_campana_60.py

# 2. Enriquecer dataset con tiempos precisos
python docs/resultado_pruebas/enriquecer_tiempos_60.py

# 3. Regenerar graficos estadisticos vectoriales (PDF) y mapa de bits (PNG)
python docs/resultado_pruebas/generar_graficas_kpis.py</code></pre>

<p>Consulta SQL directa para auditar tiempos en PostgreSQL:</p>
<pre><code>SELECT 
    b.name AS marca,
    i.content_format AS formato,
    COUNT(*) AS total_piezas,
    ROUND(AVG(i.duration_seconds)::numeric, 2) AS tiempo_medio_segundos,
    ROUND(MIN(i.duration_seconds)::numeric, 2) AS tiempo_minimo,
    ROUND(MAX(i.duration_seconds)::numeric, 2) AS tiempo_maximo
FROM ideas_generadas i
JOIN brands b ON i.brand_id = b.id
GROUP BY b.name, i.content_format
ORDER BY b.name, i.content_format;</code></pre>

<div class="page-break"></div>

<!-- SECCIÓN 7: DIAGNÓSTICO Y RESOLUCIÓN DE PROBLEMAS -->
<h1><span class="sec-num">7.</span> Árbol de Decisión y Diagnóstico de Incidencias (Troubleshooting)</h1>

<p>Ante cualquier eventualidad o comportamiento anómalo durante el levantamiento del entorno o la ejecución de las pruebas, consulte el árbol sistemático de diagnóstico en la Figura 13:</p>

<div class="figure-container">
    <img src="IMAGE_FIG_7_45" alt="Arbol Diagnostico">
    <div class="figure-caption"><strong>Figura 13:</strong> Árbol sistemático de decisión para diagnóstico y resolución de fallos en la PoC.</div>
</div>

<h2>7.1. Procedimientos Inmediatos de Resolución de Errores Comunes</h2>

<table>
    <div class="table-caption">Tabla 5: Matriz de incidencias comunes, síntomas y comandos de solución rápida.</div>
    <thead>
        <tr>
            <th>Síntoma / Error</th>
            <th>Causa Raíz Identificada</th>
            <th>Procedimiento de Solución Inmediata</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>ConnectError: host.docker.internal:11434</code></td>
            <td>Ollama no está en ejecución en Windows o falta <code>host-gateway</code> en Docker.</td>
            <td>Abra una terminal en Windows y ejecute <code>ollama serve</code>. Compruebe que <code>curl http://localhost:11434</code> responda <em>"Ollama is running"</em>.</td>
        </tr>
        <tr>
            <td><code>tool-postiz: configured: false</code></td>
            <td>Falta <code>POSTIZ_API_KEY</code> en <code>.env</code> o Postiz no está iniciado.</td>
            <td>Obtenga la API Key en <code>http://localhost:4007</code>, guárdela en <code>.env</code> y recree el contenedor: <code>docker compose up -d --no-deps --force-recreate tool-postiz</code>.</td>
        </tr>
        <tr>
            <td><code>UndefinedColumn: "platform" does not exist</code></td>
            <td>El volumen persistente de PostgreSQL no aplicó la migración 003.</td>
            <td>Ejecute: <code>docker compose exec -T postgres psql -U postgres -d ideation_db -f - &lt; migrations/003_publication_platform.sql</code>.</td>
        </tr>
        <tr>
            <td>Bloqueo en colas de RabbitMQ</td>
            <td>Mensajes acumulados por interrupción forzada de workers.</td>
            <td>Purgue las colas: <code>docker compose exec rabbitmq rabbitmqctl purge_queue ideation_queue</code>.</td>
        </tr>
    </tbody>
</table>

<div class="page-break"></div>

<!-- SECCIÓN 8: CONCLUSIONES Y RECOMENDACIONES -->
<h1><span class="sec-num">8.</span> Conclusiones y Recomendaciones para Futuros Desarrolladores</h1>

<h2>8.1. Síntesis de Validación del Objetivo Específico 4 (OE4)</h2>
<p>La implementación, ejecución y medición experimental de la Prueba de Concepto en contenedores permitió validar plenamente los compromisos asumidos en el OE4:</p>
<ol>
    <li><strong>Viabilidad Técnica Comprobada:</strong> La arquitectura multi-agente basada en microservicios desacoplados y supervisión stateless con LangGraph garantiza alta disponibilidad, trazabilidad auditada y persistencia distribuida.</li>
    <li><strong>Superación de Cuellos de Botella de ITY SAS:</strong> El tiempo de la Fase 1 disminuyó de <strong>18.83 horas a 21.44 segundos</strong> (ganancia del <strong>99.97%</strong>), eliminando el principal obstáculo operativo que frenaba al equipo de marketing digital.</li>
    <li><strong>Aseguramiento de Calidad con Supervisión Humana (HITL):</strong> La introducción de compuertas de interrupción programada en el orquestador permite que la agencia mantenga el control editorial final antes de la publicación, combinando la velocidad de los agentes con la supervisión de expertos humanos.</li>
</ol>

<h2>8.2. Recomendaciones de Escalado para ITY SAS</h2>
<ul>
    <li><strong>Despliegue Productivo en Kubernetes:</strong> Migrar los manifiestos de Docker Compose hacia Helm Charts o manifiestos de Kubernetes para habilitar escalado elástico horizontal (HPA) en función del tráfico de briefs.</li>
    <li><strong>Aceleración de Inferencia en Servidores Dedicados:</strong> Alojar los modelos LLM en servidores de inferencia con GPU (NVIDIA A10G o L4) utilizando vLLM o TGI, logrando latencias inferiores a 5 segundos por dossier.</li>
    <li><strong>Enriquecimiento Continuo de la Base Vectorial:</strong> Automatizar la ejecución periódica de <code>backfill_embeddings.py</code> para indexar de manera incremental las publicaciones que registren mejores tasas de interacción real en las redes de ITY SAS.</li>
</ul>

<div class="alert-box alert-info">
    <strong>Artefactos Entregados:</strong>
    Este manual forma parte del paquete técnico oficial de entrega de la tesis de maestría junto con el repositorio de software, los 14 contenedores Docker, los scripts de prueba empírica y los datasets anonimizados.
</div>

</body>
</html>
"""

    # Substitute image placeholders
    replacements = {
        "IMAGE_FIG_7_46": images["fig_7_46"],
        "IMAGE_FIG_7_06": images["fig_7_06"],
        "IMAGE_FIG_7_07": images["fig_7_07"],
        "IMAGE_FIG_7_08": images["fig_7_08"],
        "IMAGE_FIG_7_09": images["fig_7_09"],
        "IMAGE_FIG_7_28": images["fig_7_28"],
        "IMAGE_FIG_7_29": images["fig_7_29"],
        "IMAGE_FIG_7_30": images["fig_7_30"],
        "IMAGE_FIG_7_31": images["fig_7_31"],
        "IMAGE_FIG_7_32": images["fig_7_32"],
        "IMAGE_FIG_7_34": images["fig_7_34"],
        "IMAGE_FIG_7_35": images["fig_7_35"],
        "IMAGE_FIG_7_45": images["fig_7_45"],
    }
    
    html_content = html_template
    for placeholder, data_uri in replacements.items():
        html_content = html_content.replace(placeholder, data_uri)
    
    html_file = base_dir / "temp_manual.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("HTML source generated. Launching Playwright Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_file.as_uri(), wait_until="networkidle")
        page.wait_for_timeout(3000) # KaTeX math rendering wait
        
        page.pdf(
            path=str(output_pdf),
            format="A4",
            print_background=True,
            margin={
                "top": "16mm",
                "right": "12mm",
                "bottom": "18mm",
                "left": "12mm"
            },
            display_header_footer=True,
            header_template='<div style="font-size: 8pt; color: #64748b; width: 100%; padding: 0 15mm; display: flex; justify-content: space-between;"><span>ITY SAS &bull; Manual de Ejecución PoC Multi-Agente</span><span>Alineación con OE4</span></div>',
            footer_template='<div style="font-size: 8pt; color: #64748b; width: 100%; padding: 0 15mm; display: flex; justify-content: space-between;"><span>Documentación Técnica Oficial</span><span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span></div>'
        )
        browser.close()
        
    if html_file.exists():
        html_file.unlink()
        
    print(f"SUCCESS! PDF successfully compiled: {output_pdf}")
    print(f"PDF size: {output_pdf.stat().st_size:,} bytes")

if __name__ == "__main__":
    build_pdf()
