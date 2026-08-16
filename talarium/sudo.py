"""Sesión de sudo segura para Talarium.

Objetivo de diseño
------------------
- La contraseña se pide UNA vez por sesión y vive SOLO en memoria
  (bytearray), nunca se escribe en disco, logs ni variables de entorno.
- Con la contraseña se refresca la marca de tiempo de sudo
  (`sudo -S -v`), de forma que el usuario no vuelve a escribirla
  durante toda la sesión, aunque sudo expire a los 15 minutos.
- Al salir del programa se ejecuta `sudo -k` (invalida la marca de
  tiempo) y se sobrescribe el búfer en memoria. Ningún dato sensible
  sobrevive a la sesión.

Casos cubiertos
---------------
- Usuario root              -> comandos directos, sin sudo.
- Sin binario 'sudo'        -> error claro y accionable.
- Contraseña incorrecta     -> reintentos limitados y mensaje amigable.
- Sin terminal interactiva  -> rechazo explícito (no colgar).
- Ctrl+C / salida inesperada -> limpieza vía signal y atexit.
"""

import atexit
import os
import signal
import subprocess
import sys
from typing import List, Optional, TYPE_CHECKING

from .errors import SudoError

if TYPE_CHECKING:  # solo para anotaciones; evita import circular
    from .ui.base import UI

MAX_ATTEMPTS = 3
SUDO_TIMEOUT = 30  # segundos para cada operación de autenticación


class SudoSession:
    """Mantiene una sesión sudo validada durante toda la ejecución."""

    def __init__(self, ui: Optional["UI"] = None) -> None:
        self.ui = ui
        self._password = bytearray()   # única copia en memoria
        self._valid = False
        self._cleared = False
        self._have_sudo = bool(self._which("sudo"))
        atexit.register(self.clear)

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _which(name: str) -> Optional[str]:
        from shutil import which
        return which(name)

    @property
    def is_root(self) -> bool:
        return os.geteuid() == 0

    @property
    def available(self) -> bool:
        """True si hay algún camino para ejecutar privilegiado."""
        return self.is_root or self._have_sudo

    @property
    def authenticated(self) -> bool:
        return self._valid

    # ------------------------------------------------------------- prompts
    def _prompt_password(self, attempt: int) -> Optional[str]:
        """Pide la contraseña por la UI (dialog) o por /dev/tty (getpass)."""
        label = "Contraseña de sudo"
        if self.ui is not None and hasattr(self.ui, "password"):
            pw = self.ui.password(label, f"Intento {attempt}/{MAX_ATTEMPTS}")
            return pw
        # Sin interfaz gráfica: leer del terminal real, nunca de un pipe.
        if not os.isatty(0):
            raise SudoError(
                "No hay terminal interactiva para pedir la contraseña.\n"
                "Ejecuta Talarium desde una terminal o usa un usuario con sudo."
            )
        import getpass
        try:
            user = os.getlogin()
        except OSError:
            user = "tu usuario"
        try:
            return getpass.getpass(f"[sudo] contraseña de {user}: ")
        except (EOFError, KeyboardInterrupt):
            return None

    # ----------------------------------------------------------- validación
    def _validate(self, password: bytes) -> bool:
        """Valida la contraseña y refresca la marca de tiempo de sudo."""
        try:
            proc = subprocess.run(
                ["sudo", "-S", "-p", "", "-v"],
                input=password,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=SUDO_TIMEOUT,
            )
        except (subprocess.SubprocessError, OSError):
            return False
        return proc.returncode == 0

    def authenticate(self) -> bool:
        """Pide la contraseña y la valida. Reintenta hasta MAX_ATTEMPTS."""
        if self.is_root:
            self._valid = True
            return True
        if not self._have_sudo:
            raise SudoError(
                "Se requieren permisos de superusuario pero 'sudo' no está "
                "instalado.\nEjecuta Talarium como root o instala sudo."
            )
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                pw = self._prompt_password(attempt)
            except SudoError:
                raise
            except Exception:
                pw = None
            if pw is None:
                raise SudoError("Autenticación cancelada. Operación no realizada.")
            if self._validate(pw.encode()):
                self._store(pw.encode())
                self._valid = True
                return True
            if self.ui is not None and hasattr(self.ui, "alert"):
                self.ui.alert("sudo", f"Contraseña incorrecta (intento {attempt}/{MAX_ATTEMPTS}).")
            else:
                print(f"[sudo] Contraseña incorrecta (intento {attempt}/{MAX_ATTEMPTS}).")
        raise SudoError(
            f"Autenticación fallida tras {MAX_ATTEMPTS} intentos.\n"
            "Verifica tu contraseña o tu pertenencia al grupo sudo/wheel."
        )

    def ensure(self) -> bool:
        """Asegura una marca de tiempo de sudo válida para la siguiente operación.

        Si ya hay contraseña en memoria, refresca la marca de tiempo de forma
        silenciosa; en caso contrario vuelve a pedirla.
        """
        if self.is_root:
            return True
        if self._valid and self._password:
            if self._validate(self._password):
                return True
            self._valid = False  # expiró o cambió la clave
        return self.authenticate()

    def _store(self, password: bytes) -> None:
        """Copia la contraseña en un búfer mutable (memoria únicamente)."""
        self.clear_password()
        self._password = bytearray(password)

    def clear_password(self) -> None:
        """Sobrescribe el búfer en memoria (sin tocar la marca de sudo)."""
        if self._password:
            self._password[:] = b"\x00" * len(self._password)
        self._password = bytearray()

    def clear(self) -> None:
        """Invalida la sesión sudo y borra la contraseña de memoria."""
        if self._cleared:
            return
        if not self.is_root and self._have_sudo and self._valid:
            try:
                subprocess.run(["sudo", "-k"], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=10)
            except (subprocess.SubprocessError, OSError):
                pass
        self.clear_password()
        self._valid = False
        self._cleared = True

    # ------------------------------------------------------------- ejecución
    def run(self, argv: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Ejecuta argv con privilegios de root, con salida en vivo.

        - Como root: se ejecuta directamente.
        - Como usuario: se valida la sesión y se ejecuta con `sudo`.
        """
        if self.is_root:
            return subprocess.run(argv, **kwargs)
        self.ensure()
        kwargs.setdefault("text", True)
        return subprocess.run(["sudo"] + argv, **kwargs)

    def run_checked(self, argv: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Como run(), pero lanza SudoError si el comando falla."""
        proc = self.run(argv, **kwargs)
        if proc.returncode != 0:
            raise SudoError(
                f"El comando privilegiado falló (código {proc.returncode}):\n  {' '.join(argv)}",
                cmd=" ".join(argv), code=proc.returncode,
            )
        return proc

    def check_output(self, argv: List[str], **kwargs) -> str:
        """Ejecuta un comando privilegiado y devuelve su salida capturada."""
        kwargs.setdefault("capture_output", True)
        kwargs.setdefault("text", True)
        proc = self.run(argv, **kwargs)
        return proc.stdout or ""


def install_signal_cleanup(session: "SudoSession") -> None:
    """Asocia SIGINT/SIGTERM a una limpieza controlada de la sesión sudo."""
    def _handler(signum, frame):  # noqa: ARG001
        session.clear()
        print("\nSesión terminada por el usuario. Contraseña sudo eliminada.")
        sys.exit(130 if signum == signal.SIGINT else 143)
    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)
