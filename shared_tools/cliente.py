"""Tools para consultar perfiles de cliente."""
import logging

from .db import query_db

logger = logging.getLogger(__name__)


def get_client_profile(client_id: int) -> dict | None:
    """Obtiene el perfil completo de un cliente por su ID."""
    rows = query_db(
        "SELECT id, nombre, perfil_marca, restricciones_tono, historico, "
        "producto_servicio, audiencia_objetivo, objetivo_marketing, "
        "propuesta_valor, pilares_contenido, canales_objetivo, pais, "
        "zona_horaria, restricciones_legales "
        "FROM clientes WHERE id = %s",
        (client_id,),
    )
    if rows:
        logger.info("Perfil de cliente %s cargado", client_id)
        return rows[0]
    logger.warning("Cliente %s no encontrado", client_id)
    return None


def get_client_by_name(nombre: str) -> dict | None:
    """Busca un cliente por nombre (parcial)."""
    rows = query_db(
        "SELECT id, nombre, perfil_marca, restricciones_tono, historico "
        "FROM clientes WHERE nombre ILIKE %s LIMIT 1",
        (f"%{nombre}%",),
    )
    return rows[0] if rows else None


def list_all_clients() -> list[dict]:
    """Lista todos los clientes."""
    return query_db(
        "SELECT id, nombre, perfil_marca, producto_servicio, audiencia_objetivo, "
        "objetivo_marketing, pais FROM clientes ORDER BY id"
    )


def format_client_profile(profile: dict) -> str:
    """Formatea un perfil de cliente como texto para el prompt."""
    if not profile:
        return "No hay información de cliente disponible."
    return (
        f"Cliente: {profile.get('nombre', 'Desconocido')}\n"
        f"Perfil de marca: {profile.get('perfil_marca', 'N/A')}\n"
        f"Restricciones de tono: {profile.get('restricciones_tono', 'N/A')}\n"
        f"Producto/servicio: {profile.get('producto_servicio', 'N/A')}\n"
        f"Audiencia objetivo: {profile.get('audiencia_objetivo', 'N/A')}\n"
        f"Objetivo de marketing: {profile.get('objetivo_marketing', 'N/A')}\n"
        f"Propuesta de valor: {profile.get('propuesta_valor', 'N/A')}\n"
        f"Pilares de contenido: {profile.get('pilares_contenido', 'N/A')}\n"
        f"Canales objetivo: {profile.get('canales_objetivo', 'N/A')}\n"
        f"País/zona horaria: {profile.get('pais', 'N/A')} / "
        f"{profile.get('zona_horaria', 'N/A')}\n"
        f"Restricciones legales: {profile.get('restricciones_legales', 'N/A')}\n"
        f"Histórico: {profile.get('historico', 'N/A')}"
    )


def ensure_client_profile_fields() -> None:
    """Migra instalaciones existentes sin borrar datos del cliente."""
    from .db import execute_db

    columns = {
        "producto_servicio": "TEXT",
        "audiencia_objetivo": "TEXT",
        "objetivo_marketing": "TEXT",
        "propuesta_valor": "TEXT",
        "pilares_contenido": "TEXT",
        "canales_objetivo": "TEXT",
        "pais": "VARCHAR(80) DEFAULT 'Colombia'",
        "zona_horaria": "VARCHAR(80) DEFAULT 'America/Bogota'",
        "restricciones_legales": "TEXT",
    }
    for name, definition in columns.items():
        execute_db(f"ALTER TABLE clientes ADD COLUMN IF NOT EXISTS {name} {definition}")
