"""Contexto global de la sesión de Talarium.

Reúne todos los servicios (UI, sudo, runner, catálogo, gestor de paquetes
y distro) en un único objeto para evitar importaciones circulares y
facilitar el testeo con dobles.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .core.system import DistroInfo
from .sudo import SudoSession

if TYPE_CHECKING:
    from .core.catalog import Catalog
    from .core.packagemanager import Flatpak, PackageManager
    from .core.runner import Runner
    from .ui.base import UI


@dataclass
class Context:
    distro: DistroInfo
    ui: "UI"
    sudo: SudoSession
    runner: "Runner"
    catalog: "Catalog"
    pm: "PackageManager"
    flatpak: "Flatpak"
