# Diagramas del capítulo de arquitectura

Cada archivo `.mmd` es la fuente Mermaid editable y su PDF homónimo es la figura que incluye `capitulo_arquitectura.tex`. Edita el `.mmd` y vuelve a generar el PDF correspondiente; no edites el PDF manualmente.

## Renderizado

Requisitos: Node.js y acceso a npm la primera vez. No es necesario añadir Mermaid CLI a las dependencias de la aplicación; `npx` lo ejecuta temporalmente:

```powershell
npx --yes @mermaid-js/mermaid-cli -i docs/diagramas/01_contexto.mmd -o docs/diagramas/01_contexto.pdf
```

Para regenerar todas las figuras en PowerShell desde la raíz del repositorio:

```powershell
Get-ChildItem docs\diagramas -Filter *.mmd | ForEach-Object {
    $pdf = Join-Path $_.DirectoryName ($_.BaseName + '.pdf')
    npx --yes @mermaid-js/mermaid-cli -i $_.FullName -o $pdf
    if ($LASTEXITCODE -ne 0) { throw "Falló el renderizado de $($_.Name)" }
}
```

El capítulo LaTeX incluye los PDF por ruta relativa. Para compilarlo desde la carpeta `docs` se requiere una distribución LaTeX con `graphicx`, `pdflscape`, `booktabs`, `longtable` y paquetes base indicados al inicio del `.tex`:

```powershell
Push-Location docs
pdflatex capitulo_arquitectura.tex
pdflatex capitulo_arquitectura.tex
Pop-Location
```

La segunda pasada resuelve referencias cruzadas. Las pruebas de renderizado de Mermaid no sustituyen la compilación LaTeX.

## Inventario

| Fuente y PDF | Vista |
| --- | --- |
| `01_contexto` | Contexto de sistema C4 nivel 1. |
| `02_contenedores` | Contenedores y comunicaciones C4 nivel 2. |
| `03_componentes` | Componentes del supervisor, agentes, tools y gateway. |
| `04_secuencia_pipeline` | Secuencia de lote de ideas, preparación, aprobación y entrega. |
| `05_despliegue` | Host, Docker Compose, BFF local, Ollama y servicios externos. |
| `06_modelo_datos` | Entidades y relaciones derivadas del SQL/migraciones, incluida plataforma de publicación. |
| `07_grafos_agentes` | Transiciones de los grafos LangGraph, incluida la generación de variantes por canal. |
| `08_tool_discovery` | Descubrimiento e invocación de operaciones por manifiesto. |
| `09_bdi_flujo` | Lectura analítica BDI del flujo determinista. |
| `10_rag_multi_tenant` | Recuperación semántica con filtro de marca. |
| `11_secuencia_publicacion_postiz` | Variantes por plataforma, persistencia por variante y publicación externa condicional con Postiz. |
| `12_secuencia_fallo_recuperacion` | Checkpoints, redelivery y límites de ack. |
| `13_arquitectura_evolucion` | Composición actual y flujo del sistema. |
| `14_roadmap_capacidades` | Capacidades actuales y posibles evoluciones, claramente separadas. |
| `15_architecture-decisions` | Mapa de ADR a decisiones y componentes. |
| `16_quality_scenarios` | Escenarios de calidad y evidencia disponible. |
| `17_vincular_canal_postiz` | Catálogo, validación y asociación de una integración Postiz a una marca. |
| `18_frontend_modulos` | Módulos de la SPA React, BFF y servicios que consume cada uno. |
| `19_estados_publicacion` | Estados de una publicación entre preparación, aprobación y entrega. |
