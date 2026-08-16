"""Instalación de herramientas desde releases oficiales (GitHub / web).

Reutiliza el catálogo config/software/github.conf con el formato:
    nombre|patrón_del_asset|url|binario_destino(opcional)

Resolver -> descargar -> instalar según extensión. Errores de red,
extracción o formato se reportan sin romper el resto de la sesión.
"""

import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

from .catalog import GithubEntry
from .packagemanager import PackageManager
from .runner import Runner

_PREFERENCE = {  # extensión preferida por gestor
    "dnf": ".rpm", "zypper": ".rpm", "apt": ".deb",
    "pacman": ".pkg.tar", "xbps": ".xbps",
}


def _curl_or_urlopen(url: str) -> bytes:
    """Descarga URL con curl si existe; si no, con urllib."""
    if shutil.which("curl"):
        proc = subprocess.run(["curl", "-fsSL", url], capture_output=True, timeout=120)
        if proc.returncode == 0:
            return proc.stdout
        raise RuntimeError(f"curl falló para {url}")
    req = Request(url, headers={"User-Agent": "Talarium/1.0"})
    with urlopen(req, timeout=60) as resp:
        return resp.read()


def resolve_url(entry: GithubEntry, pm_name: str) -> Optional[str]:
    """Devuelve la URL concreta de descarga del asset adecuado."""
    name, pattern, base, _dest = entry
    if "api.github.com" in base:
        try:
            data = json.loads(_curl_or_urlopen(base).decode())
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"  No se pudo consultar la API de {name}: {exc}")
            return None
        assets = [a.get("browser_download_url", "") for a in data.get("assets", [])
                  if re.search(pattern, a.get("name", ""))]
        if not assets:
            print(f"  No se encontró un asset que coincida con '{pattern}' para {name}.")
            return None
        pref = _PREFERENCE.get(pm_name, "")
        if pref:
            for url in assets:
                if url.endswith(pref) or (pref == ".pkg.tar" and ".pkg.tar." in url):
                    return url
        return assets[0]
    return base


def _install_rpm(runner: Runner, pm: PackageManager, f: Path, name: str) -> bool:
    if pm.name in ("dnf", "zypper"):
        print(f"  Instalando {name} (rpm)...")
        return runner.priv(pm.install_cmd + [str(f)], timeout=900).returncode == 0
    print(f"  Paquete .rpm no aplica a {pm.name}: instálalo desde el repo oficial.")
    return False


def _install_deb(runner: Runner, pm: PackageManager, f: Path, name: str) -> bool:
    if pm.name != "apt":
        print(f"  Paquete .deb no aplica a {pm.name}.")
        return False
    print(f"  Instalando {name} (deb)...")
    proc = runner.priv(["dpkg", "-i", str(f)], capture=True, timeout=900)
    if proc.returncode != 0:
        runner.priv(["apt-get", "install", "-f", "-y"], capture=True, timeout=900)
    return True


def _install_pkg(runner: Runner, pm: PackageManager, f: Path, name: str) -> bool:
    if pm.name == "pacman":
        print(f"  Instalando {name} (pkg.tar)...")
        return runner.priv(["pacman", "-U", "--noconfirm", str(f)], timeout=900).returncode == 0
    print(f"  Paquete pkg.tar no aplica a {pm.name}.")
    return False


def _install_appimage(runner: Runner, f: Path, name: str, dest: str) -> bool:
    home = Path.home()
    (home / "Applications").mkdir(parents=True, exist_ok=True)
    (home / ".local" / "bin").mkdir(parents=True, exist_ok=True)
    target = home / "Applications" / f"{name}.AppImage"
    shutil.copyfile(f, target)
    target.chmod(0o755)
    link = home / ".local" / "bin" / dest
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(target)
    return True


def _extract_binary(f: Path, name: str, tmp: Path) -> Optional[Path]:
    """Extrae un tar.* y localiza el binario del mismo nombre.

    Compatible con Python 3.8+ (evita 'extractall(filter=...)' de 3.12)
    y defensivo contra rutas absolutas o traversal ('..').
    """
    try:
        with tarfile.open(f) as tar:
            members = [m for m in tar.getmembers()
                       if _safe_member(m) and not m.isdev()]
            tar.extractall(tmp, members=members)
    except (tarfile.TarError, OSError):
        return None
    for p in tmp.rglob("*"):
        if p.is_file() and p.name == name and os.access(p, os.X_OK):
            return p
    for p in tmp.rglob("*"):
        if p.is_file() and os.access(p, os.X_OK):
            return p
    return None


def _safe_member(member: tarfile.TarInfo) -> bool:
    name = member.name
    return not (name.startswith("/") or ".." in name.split("/"))


def _install_gz(runner: Runner, f: Path, name: str, dest: str) -> bool:
    home = Path.home() / ".local" / "bin"
    home.mkdir(parents=True, exist_ok=True)
    out = f.with_suffix("")
    proc = subprocess.run(["gzip", "-dkf", str(f)], capture_output=True, timeout=300)
    if proc.returncode != 0:
        return False
    if out.is_file():
        out.chmod(0o755)
        shutil.move(str(out), str(home / dest))
        return True
    return False


def install_github(runner: Runner, pm: PackageManager, entry: GithubEntry) -> bool:
    name, _pattern, _base, dest = entry
    print(f">> {name}: resolviendo enlace de descarga...")
    url = resolve_url(entry, pm.name)
    if not url:
        return False
    print(f"   {url}")

    with tempfile.TemporaryDirectory(prefix="talarium-gh-") as tdir:
        f = Path(tdir) / f"{name}.dl"
        try:
            f.write_bytes(_curl_or_urlopen(url))
        except (OSError, RuntimeError) as exc:
            print(f"  Error de descarga de {name}: {exc}")
            return False

        ext = f.suffix.lower()
        fl = f.name.lower()
        if ext == ".rpm":
            ok = _install_rpm(runner, pm, f, name)
        elif ext == ".deb":
            ok = _install_deb(runner, pm, f, name)
        elif ".pkg.tar" in fl:
            ok = _install_pkg(runner, pm, f, name)
        elif fl.endswith(".appimage"):
            ok = _install_appimage(runner, f, name, dest)
        elif fl.endswith((".tar.gz", ".tgz", ".tar.xz", ".tar.zst")):
            tmp = Path(tdir) / "x"
            tmp.mkdir()
            binpath = _extract_binary(f, name, tmp)
            if not binpath:
                print(f"  No se encontró el binario '{name}' dentro del archivo.")
                return False
            home = Path.home() / ".local" / "bin"
            home.mkdir(parents=True, exist_ok=True)
            target = home / dest
            shutil.copyfile(binpath, target)
            target.chmod(0o755)
            ok = True
        elif fl.endswith(".gz"):
            ok = _install_gz(runner, f, name, dest)
        else:
            home = Path.home() / ".local" / "bin"
            home.mkdir(parents=True, exist_ok=True)
            target = home / dest
            shutil.copyfile(f, target)
            target.chmod(0o755)
            ok = True

    if ok:
        print(f"  {name} instalado en ~/.local/bin/{dest}")
        _warn_path()
    return ok


def remove_github(name: str, dest: str) -> None:
    """Elimina un binario instalado por GitHub/AppImage."""
    home = Path.home()
    for p in (home / ".local" / "bin" / dest,
              home / "Applications" / f"{name}.AppImage"):
        try:
            if p.is_symlink() or p.is_file():
                p.unlink()
                print(f"  Eliminado: {p}")
        except OSError:
            pass


def _warn_path() -> None:
    home_bin = str(Path.home() / ".local" / "bin")
    if home_bin in os.environ.get("PATH", "").split(":"):
        return
    print("  OJO: ~/.local/bin no está en PATH. Añádelo con:")
    print(f'       echo \'export PATH="{home_bin}:$PATH"\' >> ~/.bashrc')
