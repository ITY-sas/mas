# Anexo 40. Registro de Auditoría Técnica y Catálogo de Correcciones Implementadas

<div class="meta">
<b>Capítulo:</b> 5 (Implementación y Evaluación PoC) &nbsp;|&nbsp; 
<b>Objetivo Específico:</b> OE4 &nbsp;|&nbsp; 
<b>Investigador:</b> Alvaro Felipe Lopez Russi &nbsp;|&nbsp; 
<b>Entidad:</b> ITY SAS / Universidad Católica de Colombia
</div>

## 1. Bitácora de Auditoría y Evolución del Código

Durante el ciclo de evaluación y cierre del proyecto, se ejecutaron rigurosas auditorías estáticas y dinámicas sobre el código del repositorio, identificando anomalías técnicas que fueron subsanadas formalmente en los commits de control de versiones.

---

## 2. Catálogo Exhaustivo de Correcciones Implementadas

| ID Hallazgo | Componente Afectado | Descripción de la Anomalía Técnica | Corrección Aplicada | Commit de Cierre |
|:---:|---|---|---|:---:|
| **AUD-01** | `orchestrator/main.py` | La guarda de entrega en `/deliver` permitía despachos en estado `draft` si no se validaba el payload. | Se forzó la validación estricta de estado `approved` retornando HTTP 409 Conflict (ADR-008). | `f389336` |
| **AUD-02** | `rabbitmq / compose` | La parada abrupta de RabbitMQ provocaba pérdida de mensajes no persistidos en disco. | Se vinculó el volumen durable `rabbitmq_data` y se configuró acuse manual (`basic_ack`). | `f389336` |
| **AUD-03** | `frontend / bff` | El frontend intentaba conectarse al puerto 8002 directamente violando el patrón BFF. | Se unificó la salida hacia el puerto 3000 con enrutamiento inverso hacia el supervisor. | `dd3644c` |
| **AUD-04** | `tests/integration/` | `test_ideacion_tools_endpoint` fallaba si los agentes arrancaban antes que `tool-client`. | Se incorporaron reintentos de inicialización en el ciclo de vida de FastAPI y en scripts de test. | `626b065` |
| **AUD-05** | `documentation / markdown` | Fórmulas KaTeX corruptas con caracteres de control (`\x09ext`, `\x0crac`) en documentos técnicos. | Script automatizado de saneamiento de secuencias de escape y recompilación completa. | `Auditoría Final` |
| **AUD-06** | `anexos / diagramas` | Los diagramas Mermaid salían en texto plano crudo en los PDFs compilados. | Implementación de `@mermaid-js/mermaid-cli` con renderizado a imagen de alta resolución. | `Auditoría Final` |

---

## 3. Estado Final de la Suite de Pruebas

Con las seis correcciones aplicadas y la pila Docker activa, la suite automatizada certifica la estabilidad completa del monorepo:
* **Pruebas Totales:** 261
* **Aprobadas:** 261 (100,0%)
* **Fallidas:** 0
* **Omitidas:** 0
* **Tiempo de Ejecución:** 8,02 segundos.
