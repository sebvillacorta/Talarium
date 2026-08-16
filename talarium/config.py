"""Rutas y configuración global de Talarium.

Sigue la filosofía "configurable con entorno, predecible por defecto":
- TALARIUM_ROOT : raíz del repositorio/instalación (donde vive config/).
- TALARIUM_CONFIG: directorio de configuración (config/ por defecto).
- BACKUP_BASE   : donde se guardan las copias de seguridad.
"""

import os
from pathlib import Path

ROOT = Path(os.environ.get("TALARIUM_ROOT", str(Path(__file__).resolve().parent.parent)))
CONFIG_DIR = Path(os.environ.get("TALARIUM_CONFIG", str(ROOT / "config")))
THEME_FILE = CONFIG_DIR / "theme" / "dialog.mono"
BACKUP_BASE = Path(os.environ.get("TALARIUM_BACKUPS", str(Path.home() / "Talarium-backups")))


def is_root() -> bool:
    """True si el proceso actual corre como superusuario (euid 0)."""
    return os.geteuid() == 0


def has_sudo() -> bool:
    """True si el binario 'sudo' existe y es ejecutable."""
    from shutil import which
    return which("sudo") is not None


def is_tty() -> bool:
    """True si stdin y stdout son terminales interactivas."""
    return os.isatty(0) and os.isatty(1)
