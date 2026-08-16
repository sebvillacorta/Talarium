"""Interfaz abstracta de la TUI de Talarium.

Todos los backends (dialog, whiptail, texto) implementan esta API, de modo
que los módulos de funcionalidad no dependen de la tecnología concreta.
Si un backend falla en tiempo de ejecución, la fábrica puede degradar
automáticamente al siguiente disponible.
"""

from abc import ABC, abstractmethod
from typing import Iterable, List, Optional, Sequence, Tuple

Item = Tuple[str, str]                  # (tag, etiqueta)
CheckItem = Tuple[str, str, bool]       # (tag, etiqueta, marcado)


class UI(ABC):
    """Contrato mínimo de la interfaz."""

    name = "base"

    def __init__(self) -> None:
        self.backtitle = ""

    def set_backtitle(self, active: str = "") -> None:
        """Barra de pestañas estilo Talarium: la activa entre corchetes."""
        tags = ["soft", "sys", "visual", "tips", "backup", "help", "exit"]
        names = ["Software", "Sistema", "Visual", "Consejos", "Backup", "Ayuda", "Salir"]
        bar = "".join(
            f" [{n}]" if t == active else f" {n} "
            for t, n in zip(tags, names)
        )
        self.backtitle = f"Talarium · RevOst |{bar}"

    # ------------------------------------------------------------ primitivas
    @abstractmethod
    def menu(self, title: str, subtitle: str, items: Sequence[Item]) -> Optional[str]:
        """Menú de una sola selección. Devuelve el tag elegido o None si cancela."""

    @abstractmethod
    def checklist(self, title: str, subtitle: str,
                  items: Sequence[CheckItem]) -> Optional[List[str]]:
        """Lista de selección múltiple. Devuelve los tags marcados o None."""

    @abstractmethod
    def yesno(self, title: str, text: str) -> bool:
        """Confirmación Sí/No."""

    @abstractmethod
    def alert(self, title: str, text: str) -> None:
        """Aviso con confirmación (botón OK)."""

    @abstractmethod
    def info(self, title: str, text: str) -> None:
        """Información con pausa automática."""

    @abstractmethod
    def step(self, text: str) -> None:
        """Mensaje de progreso (sin bloquear)."""

    @abstractmethod
    def password(self, title: str, text: str) -> Optional[str]:
        """Entrada de contraseña sin eco. None si se cancela."""

    @abstractmethod
    def pause(self, seconds: int = 2, text: str = "") -> None:
        """Pausa corta para que el usuario lea la salida."""

    # ------------------------------------------------------------ helpers
    def items(self, seq: Iterable[str]) -> List[Item]:
        return [(s, s) for s in seq]
