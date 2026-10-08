# Demo multi-tenant

## Objetivo

Demostrar que una marca puede generar un dossier y una publicacion usando su
perfil, su memoria RAG y sus fuentes sin consultar la memoria privada de otra
marca.

## Precondiciones

```powershell
docker compose up -d --build
```

Comprobar servicios:

```powershell
Invoke-RestMethod http://localhost:8002/health | ConvertTo-Json -Depth 5
Invoke-RestMethod http://localhost:8010/brands?organization_id=1 | ConvertTo-Json -Depth 8
```

Si la base ya existia, aplicar las migraciones una vez:

```powershell
Get-Content .\migrations\001_multi_tenant_foundation.sql |
  docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U postgres -d ideation_db
Get-Content .\migrations\002_brand_knowledge_and_channels.sql |
  docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U postgres -d ideation_db
```

## Ruta demo

La ruta es:

```text
POST http://localhost:8002/demo
```

Por defecto usa `brand_id=1` (EcoBrand), genera un Reel y espera el resultado.

```powershell
$body = @{
    brand_id = 1
    content = "Crear un Reel para presentar una crema solar natural durante el verano colombiano"
    content_format = "reel"
    wait = $true
    timeout = 300
} | ConvertTo-Json -Depth 8

$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
$response = Invoke-WebRequest -UseBasicParsing -Method Post `
  -Uri http://localhost:8002/demo `
  -ContentType "application/json; charset=utf-8" `
  -Body $bytes -TimeoutSec 360

$result = $response.Content | ConvertFrom-Json
$result | ConvertTo-Json -Depth 30 | Out-File demo-reel.json -Encoding utf8

[pscustomobject]@{
    Status = $result.status
    BrandId = $result.preproduction.brand_id
    Type = $result.preproduction.content_type
    Title = $result.preproduction.title
    Scenes = $result.preproduction.script.Count
    CameraShots = $result.preproduction.camera.Count
    IdeaId = $result.idea_id
    PublicationId = $result.publication_id
} | Format-List
```

Para probar un Post:

```powershell
$body = @{
    brand_id = 1
    content = "Crear un post estatico para la crema solar natural de EcoBrand"
    content_format = "post"
    wait = $true
} | ConvertTo-Json -Depth 8
```

Un Post debe tener `post_spec`, slides y alt text; no debe exigir guion ni
planos de cámara.

## Evidencia de LLM y RAG

```powershell
docker compose logs --since 15m llm-gateway agente-ideacion agente-publicacion |
  Select-String -Pattern "provider|model|cached|generate_idea|save_idea|generate_post|save_post"

Invoke-RestMethod http://localhost:8013/stats | ConvertTo-Json -Depth 5
```

Se espera ver `ollama/gemma3:4b`, `cached=False`, llamadas a embeddings y
nuevos IDs de idea/publicación.

## Evidencia de base de datos

```powershell
docker compose exec -T postgres psql -U postgres -d ideation_db -c `
"SELECT o.slug, b.id AS brand_id, b.name, m.client_id
 FROM organizations o
 JOIN brands b ON b.organization_id=o.id
 JOIN legacy_client_brand m ON m.brand_id=b.id
 ORDER BY b.id;"
```

Validar que no existen contenidos privados sin marca:

```powershell
docker compose exec -T postgres psql -U postgres -d ideation_db -c `
"SELECT COUNT(*) AS ideas_without_brand FROM ideas_generadas WHERE brand_id IS NULL;
 SELECT COUNT(*) AS publications_without_brand FROM publicaciones_generadas WHERE brand_id IS NULL;"
```

Ambos contadores deben ser `0`.

## Prueba anti-mezcla

1. Crear una idea exclusiva para `brand_id=1`.
2. Crear otra idea exclusiva para `brand_id=2`.
3. Ejecutar `POST /similar` con `brand_id=1`.
4. Confirmar que ningún resultado tiene `brand_id=2`.
5. Repetir la operación para `brand_id=2`.

La operación RAG exige `brand_id` y filtra antes de ordenar por similitud.

## Postiz

Postiz no es necesario para validar el dossier. Sin `POSTIZ_API_KEY`, la demo
genera y guarda contenido, pero devuelve publicación externa omitida.

Para publicar se requiere configurar la API y registrar los canales en
`brand_channels`; sólo se aceptan canales vinculados al `brand_id` de la tarea.

## Resultado esperado

La demo se considera correcta cuando:

- `/health` muestra Redis, RabbitMQ, PostgreSQL y gateway disponibles.
- `/demo` termina con `status=completed`.
- El dossier tiene campos completos según `reel` o `post`.
- Se crea una idea y una publicación con el mismo `brand_id`.
- Las llamadas del gateway muestran proveedor y modelo reales.
- RAG devuelve sólo memoria de la marca solicitante.
- Los contadores de registros sin `brand_id` son cero.
- Las pruebas anti-mezcla pasan.

## Resultado ejecutado

Fecha: 2026-10-07.

Stack levantado con Docker Compose, incluyendo PostgreSQL, Redis, RabbitMQ,
Ollama mediante el gateway y los agentes.

Demo Reel:

```text
status: completed
brand_id: 1
content_type: reel
scenes: 5
camera_shots: 5
idea_id: 43
publication_id: 28
```

Demo Post:

```text
status: completed
brand_id: 1
content_type: post
carousel_slides: 0
alt_text: true
script_scenes: 0
idea_id: 44
publication_id: 29
```

Prueba RAG con dos marcas usando la misma consulta:

```text
brand_id=1 -> 10 resultados; client_id de todos: 1
brand_id=2 -> 1 resultado; client_id de todos: 2
brand1_isolated: True
brand2_isolated: True
```

Estado de la base después de la migración:

```text
EcoBrand          -> 26 ideas, 24 publicaciones
TechStart         ->  1 idea,   1 publicación
FitLife           ->  0 ideas,  0 publicaciones
Legacy unassigned ->  4 ideas,  4 publicaciones
ideas_without_brand: 0
publications_without_brand: 0
```

Los registros `Legacy unassigned` son históricos con `client_id` desconocido;
se conservaron en cuarentena y no se asignaron a una marca real.
