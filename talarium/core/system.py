"""Detección y características del sistema.

Toda la detección es defensiva: cada llamada verifica la existencia de
archivos/comandos y devuelve valores seguros ("desconocida", 0, False)
en lugar de lanzar excepciones. Así el doctor y las recomendaciones
funcionan incluso en sistemas parcialmente rotos.
"""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import List

from ..errors import UnsupportedDistro

# ---------------------------------------------------------------- distro
_SUPPORTED = {
    "dnf": ("fedora", "rhel", "centos", "rocky", "almalinux", "nobara", "blackrhino"),
    "pacman": ("arch", "manjaro", "endeavouros", "garuda", "arcolinux", "artix",
               "archcraft", "cachyos", "endes"),
    "apt": ("debian", "ubuntu", "linuxmint", "pop", "elementary", "zorin",
            "kali", "mx", "linux-sl"),
    "zypper": ("opensuse", "suse", "sled", "sles", "opensuse-tm"),
    "xbps": ("void",),
    "apk": ("alpine",),
}


@dataclass
class DistroInfo:
    id: str = "unknown"
    name: str = "desconocida"
    version: str = "?"
    pm: str = ""            # dnf | pacman | apt | zypper | xbps | apk
    pm_bin: str = ""        # binario real (dnf/pacman/apt-get/zypper/xbps-install)
    aur_helper: str = ""    # paru | yay | ""
    is_root: bool = False
    has_sudo: bool = False
    has_flatpak: bool = False
    de: str = "other"       # gnome | kde | xfce | cinnamon | mate | other
    de_name: str = "Otro"


def _read_os_release() -> dict:
    data = {}
    path = Path("/etc/os-release")
    if not path.is_file():
        return data
    try:
        for line in path.read_text(errors="replace").splitlines():
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            data[key.strip()] = value.strip().strip('"')
    except OSError:
        pass
    return data


def detect_distro() -> DistroInfo:
    """Detecta la distribución y su gestor de paquetes."""
    info = _read_os_release()
    d = DistroInfo(
        id=info.get("ID", "unknown"),
        name=info.get("NAME", "desconocida"),
        version=info.get("VERSION_ID", "?"),
        is_root=os.geteuid() == 0,
        has_sudo=which("sudo") is not None,
        has_flatpak=which("flatpak") is not None,
    )
    d.pm = _match_pm(d.id)
    d.pm_bin = _pm_binary(d.pm)
    d.aur_helper = _detect_aur() if d.pm == "pacman" else ""
    d.de, d.de_name = detect_de()
    return d


def _match_pm(distro_id: str) -> str:
    for pm, ids in _SUPPORTED.items():
        for i in ids:
            if distro_id == i or (i in ("opensuse",) and distro_id.startswith("opensuse")):
                return pm
    return ""


def _pm_binary(pm: str) -> str:
    binmap = {
        "dnf": "dnf", "pacman": "pacman", "apt": "apt-get",
        "zypper": "zypper", "xbps": "xbps-install", "apk": "apk",
    }
    return binmap.get(pm, "")


def _detect_aur() -> str:
    for helper in ("paru", "yay"):
        if which(helper):
            return helper
    return ""


def require_supported(d: DistroInfo) -> None:
    """Lanza UnsupportedDistro si el gestor no está soportado."""
    if not d.pm:
        raise UnsupportedDistro(
            f"Tu distribución ({d.name}) no está soportada todavía.\n"
            "Gestores soportados: dnf, pacman, apt, zypper, xbps."
        )


# ---------------------------------------------------------------- escritorio
def detect_de() -> tuple:
    """Detecta el escritorio: (tag, nombre legible)."""
    env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    for key, tag, name in (
        ("gnome", "gnome", "GNOME"),
        ("kde", "kde", "KDE Plasma"),
        ("plasma", "kde", "KDE Plasma"),
        ("xfce", "xfce", "XFCE"),
        ("cinnamon", "cinnamon", "Cinnamon"),
        ("mate", "mate", "MATE"),
    ):
        if key in env:
            return tag, name
    if which("gnome-shell"):
        return "gnome", "GNOME"
    if which("plasmashell"):
        return "kde", "KDE Plasma"
    if which("xfce4-session"):
        return "xfce", "XFCE"
    return "other", "Otro"


# ---------------------------------------------------------------- info sys
def mem_gb() -> int:
    try:
        mem = subprocess.run(["free", "-g"], capture_output=True, text=True).stdout
        for line in mem.splitlines():
            if line.startswith("Mem:"):
                return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return 0


def cores() -> int:
    try:
        return os.cpu_count() or 0
    except Exception:
        return 0


def gpu_vendor() -> str:
    """nvidia | amd | intel | desconocida"""
    if which("lspci"):
        try:
            out = subprocess.run(["lspci", "-nn"], capture_output=True, text=True).stdout
            for line in out.splitlines():
                if "vga" not in line.lower() and "3d controller" not in line.lower():
                    continue
                if re.search(r"\[10de", line, re.I):
                    return "nvidia"
                if re.search(r"\[1002", line, re.I):
                    return "amd"
                if re.search(r"\[8086", line, re.I):
                    return "intel"
        except OSError:
            pass
    for card in Path("/sys/class/drm").glob("card*/device/vendor"):
        try:
            v = card.read_text().strip()
        except OSError:
            continue
        if v in ("0x10de",):
            return "nvidia"
        if v in ("0x1002",):
            return "amd"
        if v in ("0x8086",):
            return "intel"
    return "desconocida"


def is_ssd() -> bool:
    """True si no hay discos giratorios (ROTA=1)."""
    if which("lsblk") is None:
        return False
    try:
        out = subprocess.run(["lsblk", "-dn", "-o", "ROTA"],
                             capture_output=True, text=True).stdout
        return "1" not in [l.strip() for l in out.splitlines()]
    except OSError:
        return False


def is_systemd() -> bool:
    return which("systemctl") is not None and Path("/run/systemd/system").is_dir()


def has_command(*names: str) -> bool:
    return all(which(n) is not None for n in names)


def installed_list(pm: str) -> List[str]:
    """Lista de paquetes instalados (para backup). Tolerante a fallos."""
    cmd = {
        "dnf": None,  # se usa repoquery con fallback a rpm
        "pacman": ["pacman", "-Qeq"],
        "apt": ["apt-mark", "showmanual"],
        "zypper": None,
    }.get(pm)
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
        return sorted(l.strip() for l in out.splitlines() if l.strip())
    except (OSError, subprocess.SubprocessError, TypeError):
        return []
