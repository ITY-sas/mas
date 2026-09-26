"""
Tests unitarios para shared_tools.cliente
U11-U14 del plan de pruebas.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared_tools.cliente import format_client_profile, get_client_profile, list_all_clients


class TestGetClientProfile:
    """U11-U12: Obtención de perfil de cliente."""

    @pytest.mark.unit
    @pytest.mark.integration  # Requiere PostgreSQL corriendo
    def test_get_existing_client(self):
        """U11: get_client_profile(1) retorna perfil completo."""
        profile = get_client_profile(1)
        assert profile is not None
        assert "perfil_marca" in profile
        assert "restricciones_tono" in profile

    @pytest.mark.unit
    @pytest.mark.integration
    def test_get_nonexistent_client(self):
        """U12: get_client_profile(999) retorna None."""
        profile = get_client_profile(999)
        assert profile is None


class TestFormatClientProfile:
    """U13: Formateo de perfil para prompt."""

    @pytest.mark.unit
    def test_format_none(self):
        """U13: format_client_profile(None) retorna mensaje de error."""
        result = format_client_profile(None)
        assert "No hay información" in result

    @pytest.mark.unit
    def test_format_valid_profile(self):
        """U13b: format_client_profile con perfil válido."""
        profile = {
            "nombre": "TestBrand",
            "perfil_marca": "Marca de prueba",
            "restricciones_tono": "Tono formal",
            "historico": "Sin historial",
        }
        result = format_client_profile(profile)
        assert "TestBrand" in result
        assert "Marca de prueba" in result
        assert "Tono formal" in result


class TestListAllClients:
    """U14: Listado de clientes."""

    @pytest.mark.unit
    @pytest.mark.integration
    def test_list_clients(self):
        """U14: list_all_clients retorna ≥1 cliente."""
        clients = list_all_clients()
        assert isinstance(clients, list)
        assert len(clients) >= 1
