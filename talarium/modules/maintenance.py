"""Sistema: limpieza, desbloat y mantenimiento.

Operaciones: eliminar bloat, huérfanos, cachés, journal y actualización
completa (incluye Flatpak).
"""

import shutil
from pathlib import Path

from ..context import Context
from ..core.system import is_systemd
from ..errors import CommandError, SudoError
from .common import ensure_sudo, remove_packages


def menu_sistema(ctx: Context) -> None:
    ui = ctx.ui
    ui.set_backtitle("sys")
    sel = ui.menu("Sistema - limpieza y mantenimiento",
                  "",
                  [("bloat", "Eliminar software preinstalado (bloat)"),
                   ("huerf", "Limpiar paquetes huérfanos o sin uso"),
                   ("cache", "Limpiar cachés del sistema"),
                   ("journal", "Compactar registros del sistema (journal)"),
                   ("update", "Actualizar el sistema completo"),
                   ("back", "Volver al menú principal")])
    if sel == "bloat":
        debloat_pick(ctx)
    elif sel == "huerf":
        debloat_orphans(ctx)
    elif sel == "cache":
        debloat_cache(ctx)
    elif sel == "journal":
        debloat_journal(ctx)
    elif sel == "update":
        run_update_system(ctx)


# ---------------------------------------------------------------- desbloat
def debloat_pick(ctx: Context) -> None:
    ui = ctx.ui
    cands = ctx.catalog.debloat(ctx.distro.de, ctx.distro.id)
    items = [(p, p, False) for p in cands if ctx.pm.is_installed(p)]

    if not items:
        ui.alert("Desbloat", f"No se detectó software desinstalable para {ctx.distro.de_name} / {ctx.distro.name}.")
        return

    chosen = ui.checklist(f"Desbloat - {ctx.distro.de_name}",
                          "Marca con ESPACIO lo que quieras ELIMINAR",
                          items)
    if not chosen:
        ui.alert("Desbloat", "No seleccionaste nada.")
        return

    if ui.yesno("Confirmar eliminación", f"Se eliminarán del sistema:\n{' '.join(chosen)}"):
        remove_packages(ctx, chosen)
        ui.pause(2)


# ---------------------------------------------------------------- huérfanos
def debloat_orphans(ctx: Context) -> None:
    if not ensure_sudo(ctx):
        return
    try:
        code = ctx.pm.autoremove()
        if code != 0:
            ctx.ui.alert("Huérfanos", f"Autoremove terminó con código {code}.")
    except (SudoError, CommandError) as exc:
        ctx.ui.alert("Huérfanos", str(exc))
    ctx.ui.pause(2)


# ------------------------------------------------------------------- cachés
def debloat_cache(ctx: Context) -> None:
    ui = ctx.ui
    if not ensure_sudo(ctx):
        return
    try:
        code = ctx.pm.clean()
        if code != 0:
            ui.step(f"  (clean devolvió {code})")
    except (SudoError, CommandError) as exc:
        ui.alert("Cachés", str(exc))
        return

    if ctx.distro.has_flatpak:
        print(">> Flatpak sin uso...")
        ctx.runner.priv(["flatpak", "uninstall", "--unused", "-y"], timeout=600)

    print(">> Cachés de usuario (~/.cache)...")
    cache = Path.home() / ".cache"
    if cache.is_dir():
        try:
            size_before = _dir_size(cache)
            for child in cache.iterdir():
                shutil.rmtree(child, ignore_errors=True) if child.is_dir() \
                    else child.unlink(missing_ok=True)
            print(f"  Cachés liberadas: {_fmt(size_before)}")
        except OSError as exc:
            print(f"  No se pudo limpiar todo: {exc}")
    else:
        print("  No hay caché de usuario para limpiar.")
    ui.pause(2)


def _dir_size(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def _fmt(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ------------------------------------------------------------------ journal
def debloat_journal(ctx: Context) -> None:
    if not is_systemd():
        ctx.ui.alert("Journal", "Este sistema no usa systemd/journal.")
        return
    if not ensure_sudo(ctx):
        return
    try:
        ctx.runner.priv(["journalctl", "--vacuum-time=10d"], timeout=600)
        ctx.ui.step("Journal compactado (se conservaron 10 días).")
    except (SudoError, CommandError) as exc:
        ctx.ui.alert("Journal", f"No se pudo compactar: {exc}")
    ctx.ui.pause(2)


# -------------------------------------------------------------- actualizar
def run_update_system(ctx: Context) -> None:
    ui = ctx.ui
    if not ui.yesno("Actualizar sistema", "Se actualizarán todos los paquetes del sistema y Flatpak.\n¿Continuar?"):
        return
    if not ensure_sudo(ctx):
        return
    pm = ctx.pm
    try:
        if pm.name == "apt":
            ctx.runner.priv(["apt-get", "update"], timeout=1800)
            ctx.runner.priv(["apt-get", "upgrade", "-y"], timeout=3600)
        else:
            code = pm.update()
            if code != 0 and pm.name != "dnf":
                print("  (update no devolvió 0; continúo con el upgrade)")
            pm.upgrade()
    except (SudoError, CommandError) as exc:
        ui.alert("Actualización", str(exc))
        return

    if ctx.distro.has_flatpak:
        print(">> Actualizando aplicaciones Flatpak...")
        ctx.runner.priv(["flatpak", "update", "-y"], timeout=3600)
    print("  Sistema actualizado.")
    ui.pause(2)
