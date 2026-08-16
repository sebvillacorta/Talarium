"""Fábrica de backends de interfaz.

Prioridad: dialog -> whiptail -> texto. Si dialog o whiptail existen pero
fallan al ejecutarse (p. ej. libnewt roto), se degrada automáticamente.
La cadena elegida se informa en 'doctor' y en el menú de ayuda.
"""

from typing import Optional

from .base import UI
from .dialog import DialogUI, _BackendFailure


def create_ui(force: Optional[str] = None, rcfile: str = "") -> UI:
    """Crea la mejor interfaz disponible.

    force: 'dialog' | 'whiptail' | 'texto' para anular la detección.
    """
    if force:
        engine = force.lower()
        if engine in ("dialog", "whiptail"):
            try:
                return DialogUI(engine=engine, rcfile=rcfile)
            except _BackendFailure:
                pass
        if engine == "texto":
            from .text import TextUI
            return TextUI()
        # force inválido -> degrada silenciosamente
    for engine in ("dialog", "whiptail"):
        try:
            return DialogUI(engine=engine, rcfile=rcfile)
        except _BackendFailure:
            continue
    from .text import TextUI
    return TextUI()


def describe_ui(ui: UI) -> str:
    """Descripción corta del backend activo para el doctor."""
    return ui.name
