"""Excepciones propias de Talarium.

Centralizar los errores evita propagar retornos mágicos y permite
traducirlos en mensajes claros en la interfaz (fail-fast y auditable).
"""


class TalariumError(Exception):
    """Error genérico de Talarium."""


class UnsupportedDistro(TalariumError):
    """La distribución no tiene gestor de paquetes soportado."""


class SudoError(TalariumError):
    """Fallo al autenticar o ejecutar con sudo."""


class CommandError(TalariumError):
    """Un comando externo devolvió código de salida distinto de cero."""

    def __init__(self, message: str, cmd: str = "", code: int = 1) -> None:
        super().__init__(message)
        self.cmd = cmd
        self.code = code


class CatalogError(TalariumError):
    """Un archivo de catálogo (config/*.conf) es inválido o ilegible."""


class NoPackagesSelected(TalariumError):
    """El usuario no marcó ningún paquete/opción (cancelación silenciosa)."""
