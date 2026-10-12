# Guia para levantar el sistema completo

Esta guia describe el arranque local en Windows con PowerShell. El proyecto usa dos Compose independientes: el stack de agentes desde la raiz y Postiz desde `postiz/postiz-docker-compose`.

## Requisitos

- Docker Desktop iniciado y con Linux containers disponibles.
- Ollama instalado en Windows y escuchando en `localhost:11434`.
- Python 3.10 o superior para ejecutar el BFF/Studio local.
- API key de Postiz solo si se va a consultar integraciones, vincular canales o enviar publicaciones.
- Credenciales OAuth de cada red social que se vaya a conectar en Postiz. El client ID/secret OAuth de LinkedIn no reemplaza la API key de Postiz.

## Configuracion de secretos

Desde la raiz del repositorio, crea o edita `.env`. No pongas claves en comandos, capturas, archivos versionados ni chats.

```dotenv
OLLAMA_MODEL=gemma3:4b
EMBEDDING_MODEL=nomic-embed-text
LLM_FALLBACK_MODEL=mistral-nemo
POSTIZ_API_URL=http://host.docker.internal:4007/api/public/v1
POSTIZ_API_KEY=PEGA_AQUI_LA_API_KEY_DE_POSTIZ
```

`.env` esta ignorado por Git. `POSTIZ_API_URL` ya tiene ese valor por defecto en el Compose, pero dejarlo explicito facilita saber que se usa Postiz local y no Postiz Cloud.

Para LinkedIn, configura `LINKEDIN_CLIENT_ID` y `LINKEDIN_CLIENT_SECRET` en el Compose local de Postiz antes de arrancarlo. Usa una aplicacion de LinkedIn Developer y el callback/redirect que solicita Postiz. No confundas esas credenciales OAuth con `POSTIZ_API_KEY`.

## 1. Preparar Ollama

Ejecuta Ollama en Windows y descarga los modelos usados por el gateway:

```powershell
ollama pull gemma3:4b
ollama pull nomic-embed-text
ollama pull mistral-nemo
```

No cierres Ollama mientras se generen ideas o variantes.

## 2. Levantar Postiz local (opcional)

Desde la raiz del repositorio:

```powershell
Push-Location .\postiz\postiz-docker-compose
docker compose config --quiet
docker compose up -d
docker compose ps
Pop-Location
```

Abre `http://localhost:4007`, crea/inicia sesion y conecta la cuenta de LinkedIn desde Integrations/Channels. Crear el usuario de Postiz por si solo no conecta una red.

Genera una API key en Postiz Settings/API Keys y guardala como `POSTIZ_API_KEY` en el `.env` de la raiz del proyecto. La herramienta `tool-postiz` es otro contenedor, perteneciente al Compose principal; por eso llega al Postiz local mediante `host.docker.internal:4007`.

Postiz puede estar arriba aunque el catalogo aparezca vacio: primero debe existir una integracion social conectada. Si se cambia la API key o `POSTIZ_API_URL`, hay que recrear solo `tool-postiz` desde la raiz, no bajar todas las bases:

```powershell
docker compose up -d --no-deps --force-recreate tool-postiz
```

## 3. Levantar agentes, herramientas y datos

Desde la raiz del repositorio:

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Esto arranca RabbitMQ, PostgreSQL/pgvector, Redis Stack, LLM Gateway, los tool services, ambos agentes y el orquestador. `tool-postiz` tambien inicia, pero su indicador de salud quedara degradado si falta la API key.

### Migraciones en un volumen existente

En un volumen nuevo, los scripts montados en `/docker-entrypoint-initdb.d` se aplican durante la inicializacion de PostgreSQL. En un volumen ya creado, Docker no los vuelve a ejecutar. Si el esquema no tiene estas columnas/indice, aplica solo las migraciones faltantes en orden, sin borrar el volumen:

```powershell
Get-Content -Raw .\migrations\003_publication_platform.sql | docker compose exec -T postgres psql -U postgres -d ideation_db -v ON_ERROR_STOP=1
Get-Content -Raw .\migrations\004_idea_generation_batches.sql | docker compose exec -T postgres psql -U postgres -d ideation_db -v ON_ERROR_STOP=1
Get-Content -Raw .\migrations\005_brand_scoped_idea_batches.sql | docker compose exec -T postgres psql -U postgres -d ideation_db -v ON_ERROR_STOP=1
```

No uses `docker compose down -v`: `-v` elimina los volumenes de PostgreSQL y Redis.

## 4. Verificar servicios

Desde la raiz:

```powershell
Invoke-RestMethod http://localhost:8002/health | ConvertTo-Json -Depth 5
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8003/health
Invoke-RestMethod http://localhost:8013/health
Invoke-RestMethod http://localhost:8016/health
Invoke-RestMethod http://localhost:8016/available-integrations | ConvertTo-Json -Depth 5
```

El orquestador debe reportar Redis, RabbitMQ, PostgreSQL y gateway como `ok`. `tool-postiz` debe mostrar `configured: true`; `available-integrations` debe contener la cuenta social conectada. Si devuelve una lista vacia, vuelve a Postiz y completa la conexion OAuth del canal.

## 5. Abrir Studio (BFF)

El frontend no esta declarado como servicio del Compose: se ejecuta localmente. Desde la raiz:

```powershell
python -m pip install -r .\frontend\requirements.txt
$env:PORT = "3001"
python -m uvicorn frontend.server:app --host 127.0.0.1 --port 3001
```

Abre `http://127.0.0.1:3001`. Se usa 3001 para no chocar con Postiz, que publica 4007, ni con un BFF que ya ocupe 3000. Para detenerlo, `Ctrl+C` en esa terminal.

## 6. Flujo de uso

1. En **Generar**, elige marca, formato, cantidad (1-5) y brief opcional.
2. En **Trazabilidad**, sigue cada tarea del lote. En **Resultados**, cada dossier aparece conforme termina.
3. En **Biblioteca**, revisa una idea, selecciona los canales Postiz vinculados, modo y fecha si corresponde.
4. **Preparar copies para revisar** ejecuta al agente publicador y guarda las variantes. Todavia no crea posts en Postiz.
5. En **Resultados**, edita/revisa cada variante y aprueba. `draft` crea un borrador; `schedule` requiere fecha UTC; `now` pide confirmacion y publica de inmediato.
6. La tarea de entrega tiene su propia traza. Revisa el estado Postiz y el `postId`/error en Resultados y Trazabilidad.

Se recomienda probar primero con `draft`; solo despues de validar el copy y el canal usar `schedule` o `now`.

## Problemas frecuentes

- **`tool-postiz` no configurado:** confirma que `.env` esta en la raiz del Compose principal y recrea solo `tool-postiz`. No imprimas la API key para diagnosticarla.
- **Catalogo Postiz vacio:** la API key autentica el workspace, pero aun falta conectar una cuenta social dentro de Postiz.
- **`rag.save_publicacion` falla por `platform`:** aplica la migracion 003 al volumen existente.
- **Postiz responde 4xx/5xx:** abre la tarea de entrega y lee `result.postiz.error`; revisa los logs con `docker compose logs --tail 100 tool-postiz` y `docker compose -f .\postiz\postiz-docker-compose\docker-compose.yaml logs --tail 100 postiz`.
- **Cambiaste Compose o variables:** usa `docker compose up -d --build` para el servicio afectado. Evita `down -v`.

## Apagar servicios sin borrar datos

Para detener el stack principal desde la raiz:

```powershell
docker compose stop
```

Para detener Postiz desde su carpeta:

```powershell
Push-Location .\postiz\postiz-docker-compose
docker compose stop
Pop-Location
```

Los comandos `stop` conservan los volumenes. No ejecutes `down -v` salvo que deliberadamente quieras borrar los datos locales.
