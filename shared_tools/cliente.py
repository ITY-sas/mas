"""Tools para consultar perfiles de cliente."""
import logging

from .db import query_db

logger = logging.getLogger(__name__)


def get_client_profile(client_id: int) -> dict | None:
    """Obtiene el perfil completo de un cliente por su ID."""
    rows = query_db(
        "SELECT id, nombre, perfil_marca, restricciones_tono, historico "
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
        "SELECT id, nombre, perfil_marca FROM clientes ORDER BY id"
    )


def format_client_profile(profile: dict) -> str:
    """Formatea un perfil de cliente como texto para el prompt."""
    if not profile:
        return "No hay información de cliente disponible."
    return (
        f"Cliente: {profile.get('nombre', 'Desconocido')}\n"
        f"Perfil de marca: {profile.get('perfil_marca', 'N/A')}\n"
        f"Restricciones de tono: {profile.get('restricciones_tono', 'N/A')}\n"
        f"Histórico: {profile.get('historico', 'N/A')}"
    )
