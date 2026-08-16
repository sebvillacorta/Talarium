"""Software: instalar / desinstalar aplicaciones por categorías.

Los catálogos viven en config/software/<gestor>.conf y
config/software/github.conf (releases oficiales de GitHub).
"""



from ..context import Context
from ..errors import CatalogError
from ..core.github import install_github, remove_github
from .common import install_packages, remove_packages, operation_completed


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
        items.append(("uninstall", "Desinstalar herramientas instaladas"))
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
        elif sel == "uninstall":
            menu_uninstall(ctx)
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
    unavailable = set()
    for p in pkgs:
        installed = ctx.pm.is_installed(p)
        label = descs.get(p, (p, ""))[0]
        if installed:
            mark = "INSTALADO"
        elif p.startswith("flatpak:"):
            if ctx.flatpak.available:
                mark = "disponible"
            else:
                mark = "NO DISPONIBLE"
                unavailable.add(p)
        elif p.startswith("aur:"):
            mark = "disponible"
        elif ctx.pm.available(p) is False:
            mark = "NO DISPONIBLE"
            unavailable.add(p)
        else:
            mark = "disponible"
        items.append((p, f"[{mark}] {label}", installed))

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
        blocked = [p for p in chosen if p in unavailable]
        if blocked:
            if not ui.yesno("Aviso",
                            f"No están disponibles en los repos de {ctx.distro.name}:\n"
                            f"{' '.join(blocked)}\n\n¿Instalar solo los disponibles?"):
                return
            chosen = [p for p in chosen if p not in blocked]
            if not chosen:
                return
        if ui.yesno("Confirmar instalación", f"Se instalarán:\n{' '.join(chosen)}"):
            ok = install_packages(ctx, chosen)
            if ok:
                operation_completed(ctx, "Instalación completada",
                                    f"Se instalaron correctamente:\n{' '.join(chosen)}")
    elif act == "remove":
        if ui.yesno("Confirmar eliminación", f"Se eliminarán:\n{' '.join(chosen)}"):
            ok = remove_packages(ctx, chosen)
            if ok:
                operation_completed(ctx, "Desinstalación completada",
                                    f"Se desinstalaron correctamente:\n{' '.join(chosen)}")


def menu_uninstall(ctx: Context) -> None:
    """Desinstala herramientas instaladas (catálogo nativo, Flatpak y GitHub)."""
    ui = ctx.ui
    items = []
    seen = set()
    for cat, pkgs in ctx.catalog.software(ctx.distro.pm).items():
        for p in pkgs:
            if p in seen:
                continue
            seen.add(p)
            if ctx.pm.is_installed(p):
                items.append((p, f"{cat} · {p}", False))

    github = [e for e in ctx.catalog.github() if _github_installed(ctx, e[0])]
    for name, *_rest in github:
        if name in seen:
            continue
        seen.add(name)
        items.append((name, f"github · {name}", False))

    if not items:
        ui.alert("Desinstalar", "No hay herramientas instaladas detectadas en el catálogo.")
        return

    chosen = ui.checklist("Desinstalar herramientas instaladas",
                          "Marca con ESPACIO lo que quieras ELIMINAR", items)
    if not chosen:
        ui.alert("Desinstalar", "No seleccionaste ninguna herramienta.")
        return
    if not ui.yesno("Confirmar eliminación", f"Se desinstalarán:\n{' '.join(chosen)}"):
        return

    gh_names = {e[0]: e for e in ctx.catalog.github()}
    gh_chosen = [n for n in chosen if n in gh_names]
    native_chosen = [n for n in chosen if n not in gh_names]
    native_chosen += [n for n in gh_chosen if ctx.pm.is_installed(n)]

    ok = True
    if native_chosen:
        ok = remove_packages(ctx, native_chosen) and ok
    for n in gh_chosen:
        remove_github(n, gh_names[n][3])
    if ok:
        operation_completed(ctx, "Desinstalación completada",
                            f"Se desinstalaron correctamente:\n{' '.join(chosen)}")


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
            ok = True
            for name in chosen:
                entry = next((e for e in entries if e[0] == name), None)
                if entry:
                    ok = install_github(ctx.runner, ctx.pm, entry) and ok
            if ok:
                operation_completed(ctx, "Instalación completada",
                                    f"Herramientas instaladas:\n{' '.join(chosen)}")
    elif act == "remove":
        for name in chosen:
            entry = next((e for e in entries if e[0] == name), None)
            remove_github(name, entry[3] if entry else name)
        operation_completed(ctx, "Desinstalación completada",
                            f"Binarios eliminados:\n{' '.join(chosen)}")


def _github_installed(ctx: Context, name: str) -> bool:
    """True si la herramienta GitHub está instalada (nativa o en ~/.local/bin)."""
    from pathlib import Path
    if ctx.pm.is_installed(name):
        return True
    return (Path.home() / ".local" / "bin" / name).exists()
