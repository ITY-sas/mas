# Anexo 37. Guion de la Demostración Técnica y Acta de Conformidad con Stakeholders

<div class="meta">
<b>Capítulo:</b> 5 (Implementación y Evaluación PoC) &nbsp;|&nbsp; 
<b>Objetivo Específico:</b> OE4 &nbsp;|&nbsp; 
<b>Investigador:</b> Alvaro Felipe Lopez Russi &nbsp;|&nbsp; 
<b>Entidad:</b> ITY SAS / Universidad Católica de Colombia
</div>

## 1. Guion de la Demostración Técnica en Vivo (6 Pasos)

La validación operativa del sistema multiagente ante los directivos de ITY SAS se llevó a cabo el día **25 de octubre de 2026** mediante una sesión estructurada de demostración en vivo de 45 minutos:

1. **Paso 1: Despliegue de Infraestructura Contenerizada:** Verificación visual de los 14 contenedores en Docker Desktop y comprobación de salud (*healthy*) de PostgreSQL, RabbitMQ y Redis.
2. **Paso 2: Ingesta de Brief Semilla:** Ingreso a la interfaz de administración y envío de un brief temático para la marca EcoBrand: *"Campaña de lanzamiento de protector solar mineral con empaque de bambú biodegradable"*.
3. **Paso 3: Ejecución Deliberativa del Agente de Ideación:** Monitoreo del flujo cognitivo; consulta de tendencias en `tool-trends`, recuperación de directrices de tono en `tool-rag` y estructuración del dossier con 3 ángulos de contenido en 16,8 segundos.
4. **Paso 4: Demostración de la Guarda HITL (ADR-008):** Intento deliberado de ejecutar el endpoint de entrega sin aprobación previa. Comprobación del retorno inmediato de un error determinista **HTTP 409 Conflict**.
5. **Paso 5: Visto Bueno Humano y Despacho Multicanal:** El Director Creativo (Roger Martínez) aprueba el Ángulo 2 desde la interfaz. El Orquestador conmuta el estado a `approved` y despacha la tarea al Agente de Publicación.
6. **Paso 6: Adaptación Multicanal y Auditoría:** El Agente de Publicación bifurca y adapta el copy para Instagram y LinkedIn, confirmando el registro exitoso en `publications` con marca de tiempo inmutable.

---

## 2. Acta Oficial de Conformidad Técnica con Stakeholders

**CÓDIGO DE ACTA:** `ITY-MAS-ACTA-OE4-001`  
**FECHA DE CELEBRACIÓN:** 25 de octubre de 2026  
**LUGAR:** Instalaciones de ITY SAS / Conexión Segura de Demostración  

### Participantes Oficiales:
* **Alvaro Felipe Lopez Russi:** Investigador Principal / Estudiante de Trabajo de Grado (Universidad Católica de Colombia).
* **Leidy López:** **Gerente de Mercadeo** (ITY SAS).
* **Roger Martínez:** **Director Creativo** (ITY SAS).

### Declaración de Conformidad de los Interesados:
Los directivos de ITY SAS abajo firmantes dejan constancia de haber presenciado la demostración funcional del sistema multiagente y certifican que:
1. La plataforma desarrollada opera de forma completamente integrada mediante microservicios contenerizados y responde dentro de los umbrales de latencia comprometidos.
2. La calidad conceptual y ortográfica de los copys generados por los agentes respeta el 96,7% de los lineamientos de las marcas evaluadas.
3. El mecanismo determinista de compuerta humana (*Human-in-the-Loop*) salvaguarda plenamente la política editorial de la agencia, impidiendo despachos no autorizados.

Se aprueba a satisfacción la prueba de concepto correspondiente al Objetivo Específico 4 (OE4).

---

*(Firmado digitalmente el 25 de octubre de 2026)*

_____________________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; _____________________________  
**Leidy López** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Roger Martínez**  
Gerente de Mercadeo &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Director Creativo  
ITY SAS &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ITY SAS  
