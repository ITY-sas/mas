# Modelo de datos y comportamiento de la base

## 1. Capas de almacenamiento

El sistema usa tres capas distintas:

| Capa | Tecnología | Qué guarda |
|---|---|---|
| Datos de negocio | PostgreSQL + pgvector | organizaciones, marcas, documentos, memoria, publicaciones y fuentes |
| Estado de ejecución | Redis Stack | checkpoints LangGraph, tareas, caché LLM y pub/sub |
| Mensajería | RabbitMQ | eventos y RPC entre servicios |

Redis y RabbitMQ no sustituyen a PostgreSQL: Redis conserva estado operativo
reconstruible y RabbitMQ transporta mensajes. La memoria durable de la marca
vive en PostgreSQL.

## 2. Diagrama entidad-relación

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ ORGANIZATION_MEMBERS : has
    USERS ||--o{ ORGANIZATION_MEMBERS : joins
    ORGANIZATIONS ||--o{ BRANDS : owns
    BRANDS ||--o{ BRAND_MEMBERS : has
    USERS ||--o{ BRAND_MEMBERS : works_on

    CLIENTES ||--o| LEGACY_CLIENT_BRAND : maps
    BRANDS ||--o| LEGACY_CLIENT_BRAND : replaces

    BRANDS ||--o{ IDEAS_GENERADAS : owns
    BRANDS ||--o{ PUBLICACIONES_GENERADAS : owns
    IDEAS_GENERADAS ||--o{ PUBLICACIONES_GENERADAS : inspires

    ORGANIZATIONS ||--o{ BRAND_SOURCES : scopes
    BRANDS ||--o{ BRAND_SOURCES : scopes
    BRAND_SOURCES ||--o{ BRAND_DOCUMENTS : describes
    BRAND_DOCUMENTS ||--o{ BRAND_CHUNKS : splits_into
    BRAND_CHUNKS ||--o{ BRAND_EVIDENCE : supports
    BRAND_SOURCES ||--o{ BRAND_EVIDENCE : supports
    BRANDS ||--o{ BRAND_EVIDENCE : owns

    BRANDS ||--o{ BRAND_CHANNELS : publishes_to

    ORGANIZATIONS {
        bigint id PK
        string name
        string slug UK
        string status
    }
    USERS {
        bigint id PK
        string email UK
        string display_name
        string status
    }
    ORGANIZATION_MEMBERS {
        bigint organization_id FK
        bigint user_id FK
        string role
    }
    BRANDS {
        bigint id PK
        bigint organization_id FK
        string name
        string slug
        string status
        vector embedding
    }
    BRAND_MEMBERS {
        bigint brand_id FK
        bigint user_id FK
        string role
    }
    CLIENTES {
        int id PK
        string nombre
    }
    LEGACY_CLIENT_BRAND {
        int client_id FK
        bigint brand_id FK
    }
    IDEAS_GENERADAS {
        int id PK
        bigint brand_id FK
        int client_id
        uuid generation_batch_id
        smallint generation_index
        vector embedding
        text content
    }
    PUBLICACIONES_GENERADAS {
        int id PK
        bigint brand_id FK
        int client_id
        int idea_id
        string platform
        vector embedding
        text content
    }
    BRAND_SOURCES {
        bigint id PK
        bigint organization_id FK
        bigint brand_id FK
        string scope
        string source_type
        string url
        string content_hash
    }
    BRAND_DOCUMENTS {
        bigint id PK
        bigint source_id FK
        bigint organization_id FK
        bigint brand_id FK
        string scope
        text content
        string content_hash
    }
    BRAND_CHUNKS {
        bigint id PK
        bigint document_id FK
        bigint organization_id FK
        bigint brand_id FK
        string scope
        int chunk_index
        vector embedding
        text content
    }
    BRAND_EVIDENCE {
        bigint id PK
        bigint brand_id FK
        bigint source_id FK
        bigint document_id FK
        bigint chunk_id FK
        text claim
        text evidence_text
    }
    BRAND_CHANNELS {
        bigint id PK
        bigint brand_id FK
        string provider
        string external_id UK
        json settings
        string credential_reference
    }
```

## 3. Ownership y scopes

Cada registro de conocimiento tiene un alcance explícito:

```text
global         -> disponible para todas las organizaciones
organization   -> disponible para las marcas de una organización
brand          -> privado de una marca
```

La jerarquía de acceso es:

```text
usuario -> organization_members -> organización -> brand_members -> marca
```

Una búsqueda privada debe limitarse por `brand_id` antes de calcular o aplicar
la similitud vectorial. Nunca se debe recuperar todo pgvector y filtrar después
en memoria.

## 4. Flujo de onboarding

```mermaid
flowchart TD
    U[Usuario autorizado] --> O[Crear organización]
    O --> B[Crear marca]
    B --> P[Completar perfil de marca]
    P --> S[Registrar fuentes y documentos]
    S --> C[Fragmentar contenido]
    C --> E[Generar embeddings]
    E --> R[Marca lista para agentes]
    R --> CH[Conectar canales Postiz]
```

La marca no debería procesar briefs reales hasta tener estado `ready` y al
menos un perfil válido.

## 5. Flujo de persistencia de una idea

```mermaid
sequenceDiagram
    participant A as Agente de ideación
    participant T as tool-rag
    participant G as LLM Gateway
    participant P as PostgreSQL

    A->>T: POST /ideas {brand_id, client_id, content}
    T->>G: POST /v1/embeddings
    G-->>T: vector 768 dimensiones
    T->>P: INSERT ideas_generadas con brand_id + embedding
    P-->>T: idea_id
    T-->>A: envelope {id, brand_id}
```

La idea queda vinculada al `brand_id` y no debe poder guardarse sin él.
Las ideas de un lote llevan `generation_batch_id` y posición estable. El índice
único parcial `(brand_id, generation_batch_id, generation_index)` hace idempotente
la reentrega de cada tarea sin mezclar marcas; las ideas legacy pueden mantener
ambos campos batch en `NULL`.

La biblioteca consulta y abre dossiers con `brand_id` en la propia condición SQL.
El estado operativo del lote (tareas pendientes, terminadas y fallidas) vive en
Redis; el dossier completo sigue siendo durable en `ideas_generadas.content`.

## 6. Flujo de recuperación RAG

```mermaid
flowchart LR
    Q[Brief de marca] --> E[Embedding de consulta]
    E --> F[Filtro brand_id y scope]
    F --> V[pgvector cosine similarity]
    V --> M[Ideas y chunks de la marca]
    M --> C[Contexto del prompt]
    C --> L[LLM Gateway]
```

Contrato de búsqueda:

```json
{
  "brand_id": 1,
  "query": "campaña de verano sostenible",
  "limit": 3,
  "min_similarity": 0.3
}
```

La garantía principal es:

```text
todos los resultados privados deben pertenecer al brand_id solicitado
```

## 7. Flujo de publicación

```mermaid
flowchart TD
    U[Usuario selecciona idea guardada] --> IV[Validar idea por brand_id]
    IV --> C[Validar canales seleccionados de brand_channels]
    C --> P[Generar una variante por provider/plataforma]
    P --> S[Guardar copy con platform e idea_id]
    S --> R[Usuario revisa o edita cada copy]
    R --> A[Aprobación explícita de envío]
    A --> V{Canal activo y settings __type?}
    V -- no --> X[No enviar; conservar copy y reportar error]
    V -- sí --> D[Tarea del agente con variantes aprobadas]
    D --> Z[Postiz /posts con type, date, integration, value y settings]
    Z --> T[Guardar resultado/error del envío en TaskStore y traza]
```

La generación de ideas no invoca este flujo. `POST /ideas/{id}/publish` solo
prepara y persiste las variantes; `POST /publications/{task_id}/deliver` ocurre
después de revisión/aprobación y despacha al publicador con los copies editados.

`brand_channels.external_id` identifica el canal externo de Postiz. La tool no
debe aceptar un `integration_id` que no pertenezca a la marca de la tarea. La
columna nullable `publicaciones_generadas.platform` identifica la plataforma de
cada variante; los registros históricos pueden mantenerla en `NULL`. La
migración `003_publication_platform.sql` añade la columna y su índice por marca,
plataforma y fecha.

## 8. Procedencia documental

Una fuente puede originar documentos, y cada documento se divide en chunks:

```text
brand_sources
  -> brand_documents
      -> brand_chunks
          -> brand_evidence
```

Cada chunk conserva:

```text
brand_id
scope
source_id
document_id
content_hash
embedding
created_at
```

Esto permite responder:

```text
qué se recuperó
qué fuente lo originó
cuándo se obtuvo
para qué marca aplica
qué evidencia respalda el claim
```

## 9. Compatibilidad legacy

Los clientes anteriores permanecen en `clientes` temporalmente. La tabla
`legacy_client_brand` traduce:

```text
clientes.id -> brands.id
```

Los registros históricos con `client_id` desconocido se conservan bajo la marca
`Legacy unassigned` con estado `quarantined`. No deben entrar en el contexto de
ninguna marca `ready`.

## 10. Consultas de control

```sql
-- Contenido privado sin marca: debe ser cero.
SELECT COUNT(*)
FROM ideas_generadas
WHERE brand_id IS NULL;

SELECT COUNT(*)
FROM publicaciones_generadas
WHERE brand_id IS NULL;

-- Verificación de una búsqueda por marca.
SELECT id, brand_id, client_id
FROM ideas_generadas
WHERE brand_id = 1
ORDER BY created_at DESC;

-- Canales vinculados a una marca.
SELECT provider, external_id, status
FROM brand_channels
WHERE brand_id = 1;
```

## 11. Estado actual

Implementado:

- Fundaciones de organización, usuario y marca.
- Migración desde clientes existentes.
- `brand_id` en ideas y publicaciones.
- Filtro RAG por marca.
- Prueba anti-mezcla.
- Onboarding inicial de marcas.
- Ingesta de documentos, chunks y procedencia.
- Canales Postiz por marca.

Pendiente para producción:

- Autenticación y autorización real.
- Políticas de acceso por usuario.
- FK obligatoria de `publicaciones_generadas.idea_id`.
- Rotación y almacenamiento seguro de credenciales.
- Conectores oficiales de plataformas.
- Auditoría completa de accesos y cambios.
