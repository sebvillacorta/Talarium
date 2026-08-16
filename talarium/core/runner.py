"""Ejecución de comandos externos con control estricto de errores.

- Salida en vivo por defecto (el usuario ve qué hace el gestor).
- Captura opcional para consultas (is_installed, listas de paquetes).
- Comandos privilegiados a través de la SudoSession (contraseña en memoria).
- Límite de tiempo configurable para que nada cuelgue la sesión.
"""

import subprocess
from typing import Optional, Sequence

from ..errors import CommandError
from ..sudo import SudoSession


class Runner:
    def __init__(self, sudo: SudoSession) -> None:
        self.sudo = sudo

    # ------------------------------------------------------- sin privilegios
    def run(self, argv: Sequence[str], *, capture: bool = False,
            timeout: Optional[int] = None, check: bool = False) -> subprocess.CompletedProcess:
        kwargs: dict = {"text": True}
        if capture:
            kwargs["capture_output"] = True
        if timeout:
            kwargs["timeout"] = timeout
        try:
            proc = subprocess.run(list(argv), **kwargs)
        except OSError as exc:
            raise CommandError(f"No se pudo ejecutar '{argv[0]}': {exc}",
                               cmd=" ".join(argv)) from exc
        if check and proc.returncode != 0:
            raise CommandError(f"Comando falló (código {proc.returncode}): {' '.join(argv)}",
                               cmd=" ".join(argv), code=proc.returncode)
        return proc

    def check_output(self, argv: Sequence[str], *, timeout: Optional[int] = None) -> str:
        return self.run(argv, capture=True, timeout=timeout).stdout or ""

    def ok(self, argv: Sequence[str]) -> bool:
        return self.run(argv, capture=True).returncode == 0

    # ------------------------------------------------------------ con sudo
    def priv(self, argv: Sequence[str], *, capture: bool = False,
             timeout: Optional[int] = None, check: bool = False) -> subprocess.CompletedProcess:
        """Ejecuta un comando como superusuario (root directo si aplica)."""
        proc = self.sudo.run(list(argv), **({"capture_output": True} if capture else {}),
                             **({"timeout": timeout} if timeout else {}))
        if check and proc.returncode != 0:
            raise CommandError(f"Comando privilegiado falló (código {proc.returncode}): {' '.join(argv)}",
                               cmd=" ".join(argv), code=proc.returncode)
        return proc
