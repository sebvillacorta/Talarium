"""Catálogos de configuración de Talarium (config/*.conf).

Parsers tolerantes: comentarios (#), líneas en blanco, espacios de más,
formatos distintos por gestor. Si un archivo está corrupto o falta, se
informa de forma clara y la funcionalidad asociada se desactiva sin
tumbar el programa.

Formatos:
- software/<gestor>.conf :  categoria: paquete1 paquete2 ...
- software/github.conf    :  nombre|patrón_asset|url|destino(opcional)
- software/descriptions.conf: etiqueta|Nombre|Descripción
- debloat/<de|distro>.conf :  un paquete por línea
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from ..config import CONFIG_DIR
from ..errors import CatalogError

GithubEntry = tuple            # (nombre, patrón, url, destino)
Description = tuple            # (nombre_visible, descripción)


@dataclass
class Catalog:
    config_dir: Path = CONFIG_DIR

    # ----------------------------------------------------------- software
    def software(self, pm: str) -> Dict[str, List[str]]:
        """categoria -> [paquetes] para un gestor concreto."""
        path = self.config_dir / "software" / f"{pm}.conf"
        return _parse_software(path)

    def software_file(self, pm: str) -> Path:
        return self.config_dir / "software" / f"{pm}.conf"

    def github(self) -> List[GithubEntry]:
        path = self.config_dir / "software" / "github.conf"
        entries: List[GithubEntry] = []
        if not path.is_file():
            return entries
        try:
            for raw in path.read_text(errors="replace").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) < 3:
                    raise CatalogError(f"Línea inválida en {path}:\n  {raw}")
                name, pattern, url = parts[0], parts[1], parts[2]
                dest = parts[3] if len(parts) > 3 else name
                entries.append((name, pattern, url, dest))
        except OSError as exc:
            raise CatalogError(f"No se pudo leer {path}: {exc}") from exc
        return entries

    def descriptions(self) -> Dict[str, Description]:
        """etiqueta -> (nombre visible, descripción)."""
        path = self.config_dir / "software" / "descriptions.conf"
        out: Dict[str, Description] = {}
        if not path.is_file():
            return out
        for raw in path.read_text(errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                out[parts[0]] = (parts[1], parts[2])
        return out

    # ------------------------------------------------------------ debloat
    def debloat(self, de: str, distro_id: str) -> List[str]:
        """Unión de listas de bloat del escritorio y de la distro."""
        pkgs: List[str] = []
        for name in (f"{de}.conf", f"{distro_id}.conf"):
            path = self.config_dir / "debloat" / name
            if not path.is_file():
                continue
            for raw in path.read_text(errors="replace").splitlines():
                p = raw.strip()
                if p and not p.startswith("#"):
                    pkgs.append(p)
        # dedupe preservando orden
        seen = set()
        return [p for p in pkgs if not (p in seen or seen.add(p))]


def _parse_software(path: Path) -> Dict[str, List[str]]:
    cats: Dict[str, List[str]] = {}
    if not path.is_file():
        raise CatalogError(f"No hay configuración de paquetes:\n{path}")
    try:
        for raw in path.read_text(errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            cat, _, rest = line.partition(":")
            cat = cat.strip()
            if not cat:
                continue
            pkgs = [p for p in rest.split() if p]
            if pkgs:
                cats.setdefault(cat, []).extend(pkgs)
    except OSError as exc:
        raise CatalogError(f"No se pudo leer {path}: {exc}") from exc
    return cats
