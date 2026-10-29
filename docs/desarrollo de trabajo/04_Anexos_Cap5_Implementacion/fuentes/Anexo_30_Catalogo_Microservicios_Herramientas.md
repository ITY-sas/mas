# Anexo 30. Catálogo de Microservicios de Herramientas y Protocolo de Descubrimiento

<div class="meta">
<b>Capítulo:</b> 5 (Implementación y Evaluación PoC) &nbsp;|&nbsp; 
<b>Objetivo Específico:</b> OE4 &nbsp;|&nbsp; 
<b>Investigador:</b> Alvaro Felipe Lopez Russi &nbsp;|&nbsp; 
<b>Entidad:</b> ITY SAS / Universidad Católica de Colombia
</div>

## 1. El Patrón Tools-as-a-Service (TaaS)

Para evitar el acoplamiento monolítico entre la lógica de inferencia de los agentes y las librerías externas de acceso a datos, se adoptó el patrón **Tools-as-a-Service** (TaaS). Cada herramienta opera como un microservicio FastAPI independiente que expone sus capacidades mediante contratos REST estandarizados y colas RPC en RabbitMQ.

### Catálogo de los 7 Microservicios de Herramientas:
1. `tool-client` (Puerto 8010): Consulta y actualización de perfiles de marca, tonos y restricciones.
2. `tool-trends` (Puerto 8011): Ingesta de tendencias desde fuentes RSS de Google News y feeds públicos.
3. `tool-competitors` (Puerto 8012): Consulta de estrategias y publicaciones de cuentas competidoras.
4. `tool-news` (Puerto 8013): Agregación y categorización de noticias relevantes por industria.
5. `tool-trending` (Puerto 8014): Análisis de frecuencia de hashtags y términos virales emergentes.
6. `tool-rag` (Puerto 8015): Memoria semántica vectorial sobre PostgreSQL con `pgvector`.
7. `tool-postiz` (Puerto 8016): Pasarela de despacho y programación de publicaciones en redes sociales.

---

## 2. Protocolo de Descubrimiento Dinámico (*Tool Discovery*)

Cada microservicio de herramientas implementa el endpoint estandarizado:
`GET /.well-known/tool-manifest`

El manifiesto JSON describe las funciones expuestas, tipos de parámetros y esquemas de respuesta, permitiendo que los agentes descubran dinámicamente las herramientas disponibles al iniciar:

```json
{
  "name": "tool-trends",
  "version": "1.0.0",
  "description": "Servicio de consulta de tendencias de mercado para marketing digital",
  "endpoints": [
    {
      "path": "/api/v1/trends/search",
      "method": "POST",
      "summary": "Buscar tendencias por categoría temática",
      "parameters": {
        "categoria": "string",
        "limit": "integer"
      },
      "responses": {
        "200": {
          "description": "Lista de tendencias identificadas con volumen y sentimiento"
        }
      }
    }
  ]
}
```

* **Verificación de Contrato:** En la prueba de integración `test_discover_all_six_manifests`, los 6 microservicios respondieron con manifiestos válidos conforme a `validate_manifest()` en menos de 250 ms.
