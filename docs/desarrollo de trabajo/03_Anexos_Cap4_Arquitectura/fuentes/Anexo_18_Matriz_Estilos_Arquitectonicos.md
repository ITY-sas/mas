# Anexo 18. Matriz Comparativa de Estilos Arquitectónicos

<div class="meta">
<b>Capítulo:</b> 4 (Definición y Evaluación de Arquitectura) &nbsp;|&nbsp; 
<b>Objetivo Específico:</b> OE3 &nbsp;|&nbsp; 
<b>Investigador:</b> Alvaro Felipe Lopez Russi &nbsp;|&nbsp; 
<b>Entidad:</b> ITY SAS / Universidad Católica de Colombia
</div>

## 1. Introducción y Criterios de Selección

El diseño del sistema multiagente para ITY SAS exigió evaluar rigurosamente tres alternativas de estilos arquitectónicos para determinar la estructura técnica óptima capaz de combinar razonamiento cognitivo no determinista (LLMs) con transacciones comerciales de alta confiabilidad.

Las tres alternativas evaluadas fueron:
1. **Alternativa A: Monolito Modular con Agentes Embebidos.**
2. **Alternativa B: Arquitectura Orientada a Agentes Pura (BDI / JADE).**
3. **Alternativa C: Arquitectura Híbrida (Microservicios en Contenedores + Orquestación Event-Driven por AMQP + Agentes Deliberativos en LangGraph).**

---

## 2. Matriz Comparativa Multicriterio (Escala 1 a 5)

La evaluación se estructuró sobre seis atributos de calidad decisivos para la operación de la agencia:

| Criterio de Decisión | Peso Relativo | Alternativa A: Monolito Modular | Alternativa B: MAS Puro (JADE) | Alternativa C: Híbrida (Seleccionada) | Justificación Técnica de la Ponderación |
|---|:---:|:---:|:---:|:---:|---|
| **Desacoplamiento y Modularidad** | 20% | 2,5 | 4,0 | **5,0** | Permite actualizar prompts o modelos sin reiniciar el broker ni la base de datos. |
| **Resiliencia y Aislamiento de Fallos** | 20% | 2,0 | 3,0 | **5,0** | Si falla un microservicio de herramientas, el orquestador aplica fallback y reintenta. |
| **Escalabilidad Horizontal** | 15% | 2,0 | 3,5 | **4,5** | Workers AMQP escalables independientemente según la carga de briefs en cola. |
| **Gobernanza y Control HITL** | 20% | 3,0 | 2,0 | **5,0** | Guarda determinista estricta en el supervisor que bloquea publicaciones no aprobadas. |
| **Facilidad de Despliegue (Docker)** | 15% | 4,5 | 2,0 | **4,5** | Pila Docker Compose reproducible en 14 contenedores estándar. |
| **Ecosistema y Madurez en IA/LLMs** | 10% | 3,0 | 2,0 | **5,0** | Compatibilidad nativa con Python, LangGraph, Ollama y APIs OpenAPI. |
| **PUNTUACIÓN TOTAL PONDERADA** | **100%** | **2,55 / 5,00** | **2,90 / 5,00** | **4,85 / 5,00** | **La Alternativa C supera ampliamente a los otros enfoques.** |

---

## 3. Conclusión y Decisión (ADR-001)

Se seleccionó unánimemente la **Alternativa C (Arquitectura Híbrida)**, consolidada en la decisión **ADR-001**, debido a que combina el rigor transaccional y la resiliencia de los microservicios con la flexibilidad adaptativa de los agentes inteligentes.
