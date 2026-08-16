"""Backend de interfaz basado en 'dialog' (o 'whiptail').

Elección: se prefiere dialog (más widgets) y se degrada a whiptail.
Ambos se invocan por subproceso con --stdout; whiptail además necesita
NEWT_COLORS para el tema monocromo y dialog usa un DIALOGRC propio.

Si el binario falla en tiempo de ejecución se lanza la excepción interna
_BackendFailure para que la fábrica degrade a texto.
"""

import os
import subprocess
import sys
from shutil import which
from typing import List, Optional, Sequence

from .base import UI, CheckItem, Item

DIALOG_RC = ""  # se rellena desde config (evita dependencias circulares)


class _BackendFailure(RuntimeError):
    """El binario dialog/whiptail no está disponible o falló al invocarse."""


class DialogUI(UI):
    name = "dialog"

    def __init__(self, engine: str = "dialog", rcfile: str = "") -> None:
        super().__init__()
        self.engine = engine
        self._rcfile = rcfile
        if which(engine) is None:
            raise _BackendFailure(f"No se encontró el binario '{engine}'.")

    # ------------------------------------------------------- invocación
    def _args(self, widget: str, title: str, *extra: str) -> List[str]:
        cmd = [self.engine, "--stdout"]
        if self.backtitle:
            cmd += ["--backtitle", self.backtitle]
        if title:
            cmd += ["--title", title]
        cmd += [widget, *extra]
        return cmd

    def _run(self, argv: List[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        if self.engine == "dialog":
            if self._rcfile and os.path.isfile(self._rcfile):
                env["DIALOGRC"] = self._rcfile
        else:  # whiptail: tema monocromo vía NEWT_COLORS
            env["NEWT_COLORS"] = (
                "root=white,black;border=white,black;shadow=black,gray;"
                "title=white,black;button=white,black;actbutton=black,white;"
                "checkbox=white,black;actcheckbox=black,white;entry=white,black;"
                "actentry=black,white;label=white,black;listbox=white,black;"
                "actlistbox=black,white;textbox=white,black;acttextbox=black,white;"
                "helpline=white,black;sellistbox=white,black;actsellistbox=black,white"
            )
        try:
            return subprocess.run(argv, env=env, text=True,
                                  capture_output=True, timeout=timeout)
        except (OSError, subprocess.SubprocessError) as exc:
            raise _BackendFailure(f"Fallo al ejecutar {self.engine}: {exc}") from exc

    # --------------------------------------------------------- primitivas
    def menu(self, title: str, subtitle: str, items: Sequence[Item]) -> Optional[str]:
        argv = self._args("--menu", title, subtitle, "0", "0", "0")
        for tag, label in items:
            argv += [str(tag), str(label)]
        proc = self._run(argv)
        if proc.returncode in (1, 255):
            return None
        return proc.stdout.strip() or None

    def checklist(self, title: str, subtitle: str,
                  items: Sequence[CheckItem]) -> Optional[List[str]]:
        argv = self._args("--checklist", title, subtitle, "0", "0", "0")
        for tag, label, checked in items:
            argv += [str(tag), str(label), "on" if checked else "off"]
        proc = self._run(argv)
        if proc.returncode in (1, 255):
            return None
        return [t.strip() for t in proc.stdout.strip().split()] if proc.stdout.strip() else []

    def yesno(self, title: str, text: str) -> bool:
        argv = self._args("--yesno", title, text, "0", "0")
        proc = self._run(argv)
        if proc.returncode == 255:
            return False
        return proc.returncode == 0

    def alert(self, title: str, text: str) -> None:
        argv = self._args("--msgbox", title, text, "0", "0")
        self._run(argv)

    def info(self, title: str, text: str) -> None:
        argv = self._args("--msgbox", title, text, "0", "0")
        self._run(argv)

    def step(self, text: str) -> None:
        print(text, flush=True)

    def password(self, title: str, text: str) -> Optional[str]:
        argv = self._args("--passwordbox", title, text, "0", "0")
        proc = self._run(argv)
        if proc.returncode in (1, 255):
            return None
        return proc.stdout.rstrip("\n") or None

    def pause(self, seconds: int = 2, text: str = "") -> None:
        if self.engine == "dialog":
            argv = self._args("--pause", "Pausa", text or "Continuar...", "0", "0", str(seconds))
            try:
                self._run(argv, timeout=seconds + 5)
                return
            except _BackendFailure:
                pass
        if not sys.stdout.isatty():
            return
        try:
            input(text or "\nPulsa Enter para continuar...")
        except (EOFError, KeyboardInterrupt):
            pass
