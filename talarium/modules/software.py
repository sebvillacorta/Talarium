"""Software: instalar / desinstalar aplicaciones por categorías.

Los catálogos viven en config/software/<gestor>.conf y
config/software/github.conf (releases oficiales de GitHub).
"""



from ..context import Context
from ..errors import CatalogError
from ..core.github import install_github, remove_github
from .common import install_packages, remove_packages


def menu_software(ctx: Context) -> None:
    ui = ctx.ui
    ui.set_backtitle("soft")
    try:
        cats = ctx.catalog.software(ctx.distro.pm)
    except CatalogError as exc:
        ui.alert("Software", str(exc))
        return

    has_github = bool(ctx.catalog.github())

    while True:
        items: list = [(cat, " · ".join(pkgs[:3])[:58]) for cat, pkgs in cats.items()]
        if not items:
            ui.alert("Software", f"La configuración está vacía:\n{ctx.catalog.software_file(ctx.distro.pm)}")
            return
        items.append(("back", "Volver al panel principal"))
        if has_github:
            items.append(("github", "Herramientas desde GitHub (releases oficiales)"))

        sel = ui.menu("Software - categorías",
                      f"Lista de paquetes para {ctx.distro.pm} en {ctx.distro.name} {ctx.distro.version}",
                      items)
        if not sel or sel == "back":
            return
        if sel == "github":
            menu_github(ctx)
        else:
            show_category(ctx, sel)


def show_category(ctx: Context, cat: str) -> None:
    ui = ctx.ui
    cats = ctx.catalog.software(ctx.distro.pm)
    pkgs = cats.get(cat)
    if not pkgs:
        ui.alert("Software", f"La categoría '{cat}' no tiene paquetes definidos.")
        return

    descs = ctx.catalog.descriptions()
    items = []
    for p in pkgs:
        installed = ctx.pm.is_installed(p)
        label = descs.get(p, (p, ""))[0]
        items.append((p, f"[{'INSTALADO' if installed else 'disponible'}] {label}", installed))

    chosen = ui.checklist(f"Software: {cat}",
                          "Marca con ESPACIO los paquetes (los ya instalados vienen marcados)",
                          items)
    if chosen is None:
        return
    if not chosen:
        ui.alert("Software", "No seleccionaste ningún paquete.")
        return

    act = ui.menu(f"Acción para: {cat}",
                  f"Paquetes seleccionados: {' '.join(chosen)}",
                  [("install", "INSTALAR los paquetes seleccionados"),
                   ("remove", "ELIMINAR los paquetes seleccionados"),
                   ("back", "Volver")])
    if act == "install":
        if ui.yesno("Confirmar instalación", f"Se instalarán:\n{' '.join(chosen)}"):
            install_packages(ctx, chosen)
            ui.pause(2)
    elif act == "remove":
        if ui.yesno("Confirmar eliminación", f"Se eliminarán:\n{' '.join(chosen)}"):
            remove_packages(ctx, chosen)
            ui.pause(2)


# ================================================================== GitHub
def menu_github(ctx: Context) -> None:
    ui = ctx.ui
    entries = ctx.catalog.github()
    if not entries:
        ui.alert("Software", "El catálogo de GitHub está vacío.")
        return

    descs = ctx.catalog.descriptions()
    items = []
    for name, _pat, _url, _dest in entries:
        label = descs.get(name, (name, ""))[0]
        installed = _github_installed(ctx, name)
        items.append((name, f"[{'INSTALADO' if installed else 'descargar'}] {label}", installed))

    chosen = ui.checklist("Software: GitHub (releases oficiales)",
                          "Descargas desde repositorios oficiales de GitHub / web del proyecto",
                          items)
    if not chosen:
        return

    act = ui.menu("Acción para GitHub",
                  f"Seleccionadas: {' '.join(chosen)}",
                  [("install", "DESCARGAR e instalar las seleccionadas"),
                   ("remove", "Eliminar binario local de las seleccionadas"),
                   ("back", "Volver")])
    if act == "install":
        if ui.yesno("Confirmar descarga", f"Se descargarán e instalarán:\n{' '.join(chosen)}"):
            for name in chosen:
                entry = next((e for e in entries if e[0] == name), None)
                if entry:
                    install_github(ctx.runner, ctx.pm, entry)
            ui.pause(2)
    elif act == "remove":
        for name in chosen:
            entry = next((e for e in entries if e[0] == name), None)
            remove_github(name, entry[3] if entry else name)
        ui.pause(2)


def _github_installed(ctx: Context, name: str) -> bool:
    """True si la herramienta GitHub está instalada (nativa o en ~/.local/bin)."""
    from pathlib import Path
    if ctx.pm.is_installed(name):
        return True
    return (Path.home() / ".local" / "bin" / name).exists()
