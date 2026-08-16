"""Backend de interfaz de texto plano (último recurso).

Sin dialog ni whiptail, Talarium sigue siendo 100% funcional con menús
numerados. Está pensado también para terminales no interactivas
(cron, scripts), donde cualquier TUI no haría más que colgar.
"""

import sys
from typing import List, Optional, Sequence

from .base import UI, CheckItem, Item


def _read(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit(0)


class TextUI(UI):
    name = "texto"

    def menu(self, title: str, subtitle: str, items: Sequence[Item]) -> Optional[str]:
        self._print_header(title, subtitle)
        for i, (tag, label) in enumerate(items, start=1):
            print(f"  {i}. {label}")
        print("  0. Volver")
        sel = _read("  Opción: ")
        if not sel.isdigit() or int(sel) < 1 or int(sel) > len(items):
            return None
        return items[int(sel) - 1][0]

    def checklist(self, title: str, subtitle: str,
                  items: Sequence[CheckItem]) -> Optional[List[str]]:
        self._print_header(title, subtitle)
        print("  (escribe los números separados por espacios; [x] = instalado/activo)")
        chosen: List[str] = []
        for i, (tag, label, checked) in enumerate(items, start=1):
            mark = "x" if checked else " "
            print(f"  [{mark}] {i}. {label}")
        sel = _read("  Selección (o Enter para cancelar): ")
        if not sel:
            return None
        for token in sel.replace(",", " ").split():
            if token.isdigit() and 1 <= int(token) <= len(items):
                chosen.append(items[int(token) - 1][0])
        return chosen or None

    def yesno(self, title: str, text: str) -> bool:
        self._print_header(title, text)
        return _read("  ¿Continuar? [s/N]: ").lower() in ("s", "y", "si", "yes")

    def alert(self, title: str, text: str) -> None:
        self._print_header(title, text)
        if sys.stdin.isatty():
            _read("  (Enter para continuar)")

    def info(self, title: str, text: str) -> None:
        self._print_header(title, text)

    def step(self, text: str) -> None:
        print(text, flush=True)

    def password(self, title: str, text: str) -> Optional[str]:
        import getpass
        self._print_header(title, text)
        if not sys.stdin.isatty():
            return None
        try:
            return getpass.getpass("  Contraseña: ")
        except (EOFError, KeyboardInterrupt):
            return None

    def pause(self, seconds: int = 2, text: str = "") -> None:
        if sys.stdin.isatty():
            _read(text or "\nPulsa Enter para continuar...")

    # ------------------------------------------------------------- helpers
    def _print_header(self, title: str, subtitle: str) -> None:
        print(f"\n== {title} ==")
        for line in subtitle.splitlines():
            print(f"   {line}")
