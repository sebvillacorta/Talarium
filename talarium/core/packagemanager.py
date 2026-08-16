"""Abstracción de gestores de paquetes.

Cada gestor implementa operaciones homogéneas (instalar, eliminar,
actualizar, limpiar...). Los prefijos de paquetes se resuelven aquí:

- 'flatpak:ID' -> operación vía Flatpak (Flathub).
- 'aur:NOMBRE' -> operación vía helper AUR (paru/yay, sólo pacman).
- resto        -> paquete nativo del gestor activo.

Disponibilidad (available/available_batch): consulta los repos de la
distro activa para saber si un paquete existe. Devuelve True/False, o
None cuando no se puede determinar (sin metadatos, sin red, error), que
se trata como "disponible" para no penalizar al usuario.

Comportamiento defensivo:
- is_installed() nunca falla: devuelve False ante cualquier error.
- install() omite paquetes ya instalados y reintenta uno a uno los que
  apt/zypper rechazan en lote (evita perder una transacción completa).
- Cada operación comprueba el código de salida y avisa con claridad.
"""

import re
from typing import Dict, List, Optional, Sequence

from ..errors import CommandError
from ..core.runner import Runner


class PackageManager:
    name = "generic"
    install_cmd: List[str] = []
    remove_cmd: List[str] = []
    update_cmd: List[str] = []
    upgrade_cmd: List[str] = []
    autoremove_cmd: List[str] = []
    clean_cmd: List[str] = []
    search_cmd: List[str] = []
    query_cmd: List[str] = []

    def __init__(self, runner: Runner) -> None:
        self.r = runner
        self._avail_cache: Dict[str, Optional[bool]] = {}

    # ------------------------------------------------------------- consultas
    def is_installed(self, pkg: str) -> bool:
        if pkg.startswith("flatpak:"):
            return self.r.ok(["flatpak", "info", pkg[len("flatpak:"):]])
        if pkg.startswith("aur:"):
            return self.r.ok([self.query_cmd[0], pkg[len("aur:"):]])
        return self.r.ok(self.query_cmd + [pkg])

    def list_installed(self) -> List[str]:
        return []

    def available(self, pkg: str) -> Optional[bool]:
        """True si existe en los repos, False si no, None si no se puede saber."""
        return None

    def available_batch(self, pkgs: Sequence[str]) -> Dict[str, Optional[bool]]:
        """Consulta la disponibilidad de varios paquetes (usa la caché)."""
        return {p: self.available(p) for p in pkgs}

    # ----------------------------------------------------------- operaciones
    def install(self, pkgs: Sequence[str]) -> None:
        """Instala paquetes nativos, con manejo de retorno y reintento."""
        pend = [p for p in pkgs if not p.startswith(("flatpak:", "aur:"))]
        self._install_native(pend)

    def _install_native(self, pend: List[str]) -> None:
        if not pend:
            return
        print(f">> Instalando: {' '.join(pend)}")
        proc = self.r.priv(self.install_cmd + pend, timeout=1800)
        if proc.returncode == 0:
            return
        if self.name in ("apt", "zypper"):
            print("  Reintento individual (alguno no estaba disponible)...")
            for p in pend:
                r = self.r.priv(self.install_cmd + [p], capture=True, timeout=900)
                if r.returncode != 0:
                    print(f"  No disponible: {p}")
            return
        raise CommandError(
            f"Fallo al instalar con {self.name} (código {proc.returncode}).",
            cmd=" ".join(self.install_cmd + pend), code=proc.returncode)

    def remove(self, pkgs: Sequence[str]) -> None:
        pend = [p for p in pkgs if not p.startswith(("flatpak:", "aur:"))]
        pend = [p for p in pend if self.is_installed(p)]
        if not pend:
            print("  Nada que eliminar (no instalado).")
            return
        print(f">> Eliminando: {' '.join(pend)}")
        proc = self.r.priv(self.remove_cmd + pend, timeout=1800)
        if proc.returncode != 0:
            raise CommandError(
                f"Fallo al eliminar con {self.name} (código {proc.returncode}).",
                cmd=" ".join(self.remove_cmd + pend), code=proc.returncode)

    def autoremove(self) -> int:
        return self.r.priv(self.autoremove_cmd, timeout=1800).returncode

    def clean(self) -> int:
        return self.r.priv(self.clean_cmd, timeout=600).returncode

    def update(self) -> int:
        return self.r.priv(self.update_cmd, timeout=1800).returncode

    def upgrade(self) -> int:
        return self.r.priv(self.upgrade_cmd, timeout=3600).returncode

    # --------------------------------------------------- personalizaciones
    def font_packages(self) -> List[str]:
        return []

    def zsh_package(self) -> str:
        return "zsh"


# --------------------------------------------------------------------- dnf
class DnfPM(PackageManager):
    name = "dnf"
    install_cmd = ["dnf", "install", "-y", "--skip-broken"]
    remove_cmd = ["dnf", "remove", "-y"]
    update_cmd = ["dnf", "check-update"]
    upgrade_cmd = ["dnf", "upgrade", "-y"]
    autoremove_cmd = ["dnf", "autoremove", "-y"]
    clean_cmd = ["dnf", "clean", "all"]
    search_cmd = ["dnf", "search"]
    query_cmd = ["rpm", "-q"]

    def list_installed(self) -> List[str]:
        out = self.r.check_output(["dnf", "repoquery", "--userinstalled"], timeout=120)
        if not out.strip():
            out = self.r.check_output(["rpm", "-qa", "--qf", "%{NAME}\\n"], timeout=120)
        return sorted(l for l in out.splitlines() if l.strip())

    def font_packages(self) -> List[str]:
        return ["jetbrains-mono-fonts", "fira-code-fonts"]

    def available_batch(self, pkgs: Sequence[str]) -> Dict[str, Optional[bool]]:
        """dnf repoquery en una sola llamada; parsea los nombres de la salida."""
        pend = [p for p in pkgs if p not in self._avail_cache]
        for p in pend:
            self._avail_cache[p] = None
        if pend:
            try:
                proc = self.r.run(["dnf", "repoquery", "--quiet"] + pend,
                                  capture=True, timeout=60)
            except Exception:  # noqa: BLE001 - sin metadatos/red: desconocido
                return dict(self._avail_cache)
            if proc.returncode == 0:
                found = set()
                for line in (proc.stdout or "").splitlines():
                    m = re.match(r"^(.*?)-[0-9]", line)
                    if m:
                        found.add(m.group(1))
                for p in pend:
                    self._avail_cache[p] = p in found
        return dict(self._avail_cache)


# ------------------------------------------------------------------ pacman
class PacmanPM(PackageManager):
    name = "pacman"
    install_cmd = ["pacman", "-S", "--noconfirm", "--needed"]
    remove_cmd = ["pacman", "-Rns", "--noconfirm"]
    update_cmd = ["pacman", "-Sy"]
    upgrade_cmd = ["pacman", "-Syu", "--noconfirm"]
    autoremove_cmd = ["pacman", "-Rns", "--noconfirm"]
    clean_cmd = ["pacman", "-Scc", "--noconfirm"]
    search_cmd = ["pacman", "-Ss"]
    query_cmd = ["pacman", "-Q"]

    def autoremove(self) -> int:
        out = self.r.check_output(["pacman", "-Qdtq"], timeout=120)
        orphans = [l for l in out.splitlines() if l.strip()]
        if not orphans:
            print("  No hay paquetes huérfanos.")
            return 0
        print(f">> Eliminando huérfanos: {' '.join(orphans)}")
        return self.r.priv(self.remove_cmd + orphans, timeout=1800).returncode

    def list_installed(self) -> List[str]:
        return sorted(l for l in self.r.check_output(["pacman", "-Qeq"], timeout=120)
                      .splitlines() if l.strip())

    def font_packages(self) -> List[str]:
        return ["ttf-jetbrains-mono", "ttf-fira-code"]

    def available(self, pkg: str) -> Optional[bool]:
        if pkg in self._avail_cache:
            return self._avail_cache[pkg]
        try:
            proc = self.r.run(["pacman", "-Si", pkg], capture=True, timeout=30)
        except Exception:  # noqa: BLE001 - sin base sincronizada: desconocido
            return None
        if (proc.stdout or "").strip():
            self._avail_cache[pkg] = True
        elif "was not found" in (proc.stderr or ""):
            self._avail_cache[pkg] = False
        else:
            return None
        return self._avail_cache[pkg]


# ---------------------------------------------------------------------- apt
class AptPM(PackageManager):
    name = "apt"
    install_cmd = ["apt-get", "install", "-y"]
    remove_cmd = ["apt-get", "purge", "-y"]
    update_cmd = ["apt-get", "update"]
    upgrade_cmd = ["apt-get", "upgrade", "-y"]
    autoremove_cmd = ["apt-get", "autoremove", "-y", "--purge"]
    clean_cmd = ["apt-get", "clean"]
    search_cmd = ["apt-cache", "search"]
    query_cmd = ["dpkg", "-s"]

    def list_installed(self) -> List[str]:
        return sorted(l for l in self.r.check_output(["apt-mark", "showmanual"], timeout=120)
                      .splitlines() if l.strip())

    def font_packages(self) -> List[str]:
        return ["fonts-jetbrains-mono", "fonts-firacode"]

    def available(self, pkg: str) -> Optional[bool]:
        if pkg in self._avail_cache:
            return self._avail_cache[pkg]
        try:
            proc = self.r.run(["apt-cache", "show", pkg], capture=True, timeout=30)
        except Exception:  # noqa: BLE001
            return None
        if (proc.stdout or "").strip():
            self._avail_cache[pkg] = True
        elif proc.returncode == 100:
            self._avail_cache[pkg] = False
        else:
            return None
        return self._avail_cache[pkg]


# -------------------------------------------------------------------- zypper
class ZypperPM(PackageManager):
    name = "zypper"
    install_cmd = ["zypper", "install", "-y"]
    remove_cmd = ["zypper", "remove", "-y"]
    update_cmd = ["zypper", "refresh"]
    upgrade_cmd = ["zypper", "update", "-y"]
    autoremove_cmd = ["zypper", "remove", "-y", "--clean-deps"]
    clean_cmd = ["zypper", "clean", "-a"]
    search_cmd = ["zypper", "search"]
    query_cmd = ["rpm", "-q"]

    def list_installed(self) -> List[str]:
        out = self.r.check_output(
            ["zypper", "se", "--installed-only", "--no-headings"], timeout=120)
        pkgs = sorted({p for p in (l.split()[-1] if l.split() else "" for l in out.splitlines())
                       if p})
        if not pkgs:
            pkgs = [l.strip() for l in
                    self.r.check_output(["rpm", "-qa", "--qf", "%{NAME}\\n"], timeout=120)
                    .splitlines() if l.strip()]
        return pkgs

    def font_packages(self) -> List[str]:
        return ["jetbrains-mono-fonts", "fira-code-fonts"]

    def available(self, pkg: str) -> Optional[bool]:
        if pkg in self._avail_cache:
            return self._avail_cache[pkg]
        try:
            proc = self.r.run(["zypper", "se", "-x", "--no-headings", pkg],
                              capture=True, timeout=30)
        except Exception:  # noqa: BLE001
            return None
        if (proc.stdout or "").strip():
            self._avail_cache[pkg] = True
        elif proc.returncode == 0:
            self._avail_cache[pkg] = False
        else:
            return None
        return self._avail_cache[pkg]


# --------------------------------------------------------------------- xbps
class XbpsPM(PackageManager):
    name = "xbps"
    install_cmd = ["xbps-install", "-y"]
    remove_cmd = ["xbps-remove", "-y", "-R"]
    update_cmd = ["xbps-install", "-Sy"]
    upgrade_cmd = ["xbps-install", "-Su"]
    autoremove_cmd = ["xbps-remove", "-yo"]
    clean_cmd = ["xbps-remove", "-O"]
    search_cmd = ["xbps-query", "-Rs"]
    query_cmd = ["xbps-query"]

    def list_installed(self) -> List[str]:
        out = self.r.check_output(["xbps-query", "-l"], timeout=120)
        pkgs = []
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].startswith("ii"):
                pkgs.append(parts[1].rsplit("-", 1)[0])
        return sorted(pkgs)

    def available(self, pkg: str) -> Optional[bool]:
        if pkg in self._avail_cache:
            return self._avail_cache[pkg]
        try:
            proc = self.r.run(["xbps-query", "-Rs", pkg], capture=True, timeout=30)
        except Exception:  # noqa: BLE001
            return None
        if (proc.stdout or "").strip():
            self._avail_cache[pkg] = True
        elif proc.returncode in (0, 1):
            self._avail_cache[pkg] = False
        else:
            return None
        return self._avail_cache[pkg]


# ---------------------------------------------------------------------- apk
class ApkPM(PackageManager):
    name = "apk"
    install_cmd = ["apk", "add"]
    remove_cmd = ["apk", "del"]
    update_cmd = ["apk", "update"]
    upgrade_cmd = ["apk", "upgrade"]
    autoremove_cmd = ["apk", "cache", "clean"]
    clean_cmd = ["apk", "cache", "clean"]
    search_cmd = ["apk", "search"]
    query_cmd = ["apk", "info", "-e"]

    def list_installed(self) -> List[str]:
        return sorted(l for l in self.r.check_output(["apk", "info", "-q"], timeout=120)
                      .splitlines() if l.strip())

    def font_packages(self) -> List[str]:
        return ["font-jetbrainsmono-ttf", "font-fira-code-ttf"]

    def available(self, pkg: str) -> Optional[bool]:
        if pkg in self._avail_cache:
            return self._avail_cache[pkg]
        try:
            proc = self.r.run(["apk", "search", "-e", pkg], capture=True, timeout=30)
        except Exception:  # noqa: BLE001 - sin índice de repos: desconocido
            return None
        if (proc.stdout or "").strip():
            self._avail_cache[pkg] = True
        elif proc.returncode in (0, 1):
            self._avail_cache[pkg] = False
        else:
            return None
        return self._avail_cache[pkg]


def factory(runner: Runner, pm_name: str) -> PackageManager:
    """Crea el gestor de paquetes para el nombre dado."""
    classes = {
        "dnf": DnfPM, "pacman": PacmanPM, "apt": AptPM,
        "zypper": ZypperPM, "xbps": XbpsPM, "apk": ApkPM,
    }
    cls = classes.get(pm_name)
    if cls is None:
        raise CommandError(f"Gestor de paquetes no soportado: {pm_name}")
    return cls(runner)


# ================================================================== flatpak
class Flatpak:
    """Operaciones de Flatpak/Flathub compartidas por todos los gestores."""

    def __init__(self, runner: Runner, has_flatpak: bool) -> None:
        self.r = runner
        self.available = has_flatpak

    def is_installed(self, appid: str) -> bool:
        return self.available and self.r.ok(["flatpak", "info", appid])

    def ensure_flathub(self) -> None:
        if not self.available:
            raise CommandError("flatpak no está instalado.")
        remotes = self.r.check_output(["flatpak", "remotes"], timeout=60).lower()
        if "flathub" not in remotes:
            print(">> Añadiendo repositorio Flathub...")
            self.r.priv(["flatpak", "remote-add", "--if-not-exists", "flathub",
                         "https://flathub.org/repo/flathub.flatpakrepo"], timeout=300)

    def install(self, appids: Sequence[str]) -> None:
        if not self.available:
            raise CommandError("flatpak no está instalado. Instálalo en la categoría 'esenciales'.")
        self.ensure_flathub()
        print(f">> Instalando (Flatpak): {' '.join(appids)}")
        proc = self.r.priv(["flatpak", "install", "-y", "flathub"] + list(appids), timeout=1800)
        if proc.returncode != 0:
            raise CommandError("Fallo al instalar paquetes Flatpak.")

    def remove(self, appids: Sequence[str]) -> None:
        if not self.available:
            return
        print(f">> Eliminando (Flatpak): {' '.join(appids)}")
        self.r.priv(["flatpak", "uninstall", "-y"] + list(appids), timeout=900)
