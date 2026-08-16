"""Copia de seguridad y restauración (paquetes + configuración dconf)."""

import datetime
import subprocess
from pathlib import Path
from shutil import which

from ..config import BACKUP_BASE
from ..context import Context
from .common import ensure_sudo


def menu_backup(ctx: Context) -> None:
    ui = ctx.ui
    ui.set_backtitle("backup")
    sel = ui.menu("Copia de seguridad", "",
                  [("create", "Crear copia (paquetes instalados + configuración)"),
                   ("restore", "Restaurar desde la copia más reciente"),
                   ("list", "Ver copias existentes"),
                   ("back", "Volver al menú principal")])
    if sel == "create":
        backup_create(ctx)
    elif sel == "restore":
        backup_restore(ctx)
    elif sel == "list":
        backup_list(ctx)


def _list_backups() -> list:
    base = Path(BACKUP_BASE)
    if not base.is_dir():
        return []
    try:
        return sorted((p for p in base.iterdir() if p.is_dir()), reverse=True)
    except OSError:
        return []


# ------------------------------------------------------------------- crear
def backup_create(ctx: Context) -> None:
    ui = ctx.ui
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = Path(BACKUP_BASE) / stamp
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        ui.alert("Backup", f"No se pudo crear el directorio {dest}:\n{exc}")
        return

    ui.step(f"Creando copia de seguridad\n>> {dest}")
    pm = ctx.pm

    if pm.name == "zypper":
        try:
            out = ctx.runner.check_output(["zypper", "se", "--installed-only", "--no-headings"],
                                          timeout=120)
            pkgs = sorted({l.split()[-1] for l in out.splitlines() if l.split()})
        except Exception:  # noqa: BLE001 - fallback rpm
            pkgs = ctx.runner.check_output(["rpm", "-qa", "--qf", "%{NAME}\\n"],
                                           timeout=120).splitlines()
        pkgs = [p for p in pkgs if p.strip()]
    else:
        pkgs = pm.list_installed()

    if pkgs:
        try:
            (dest / "paquetes.txt").write_text("\n".join(pkgs) + "\n")
            ui.step(f"  {len(pkgs)} paquetes exportados.")
        except OSError as exc:
            ui.alert("Backup", f"No se pudo escribir el listado:\n{exc}")

    if which("dconf"):
        dump = subprocess.run(["dconf", "dump", "/"], capture_output=True, timeout=120)
        if dump.returncode == 0:
            (dest / "dconf.dump").write_text(dump.stdout.decode(errors="replace"))
            ui.step("  Configuración del escritorio exportada.")

    _show_recent(ui)
    ui.pause(2)


def _show_recent(ui) -> None:
    recent = _list_backups()[:5]
    ui.step("  Copias existentes:")
    for p in recent:
        ui.step(f"    - {p.name}")


# ------------------------------------------------------------------- listar
def backup_list(ctx: Context) -> None:
    items = _list_backups()
    if not items:
        ctx.ui.alert("Backup", "No hay copias de seguridad todavía.")
        return
    names = "\n".join(f"• {p.name}" for p in items[:10])
    ctx.ui.alert("Backup", f"Copias existentes:\n\n{names}")


# ---------------------------------------------------------------- restaurar
def backup_restore(ctx: Context) -> None:
    ui = ctx.ui
    items = _list_backups()
    if not items:
        ui.alert("Backup", "No hay copias de seguridad.")
        return
    latest = items[0]
    if not ui.yesno("Restaurar",
                    f"Se restaurará la copia:\n{latest.name}\n\nEsto reinstalará los paquetes que falten."):
        return
    if not ensure_sudo(ctx):
        return

    pkg_file = latest / "paquetes.txt"
    if not pkg_file.is_file():
        ui.alert("Backup", f"No se encontró el listado de paquetes en {latest.name}.")
        return

    ui.step("Restaurando paquetes (se omiten los ya instalados)")
    missing = [p.strip() for p in pkg_file.read_text(errors="replace").splitlines()
               if p.strip() and not ctx.pm.is_installed(p.strip())]
    n = 0
    for pkg in missing:
        try:
            ctx.runner.priv(ctx.pm.install_cmd + [pkg], capture=True, timeout=900)
            n += 1
        except Exception as exc:  # noqa: BLE001 - continúa con el resto
            print(f"  No disponible: {pkg} ({exc.__class__.__name__})")
    print(f"  Paquetes reinstalados: {n}")

    dump = latest / "dconf.dump"
    if dump.is_file() and which("dconf"):
        if ui.yesno("Configuración", "¿Restaurar también la configuración del escritorio?"):
            subprocess.run(["dconf", "load", "/"], stdin=dump.open("rb"), timeout=300)
            print("  Configuración restaurada.")
    ui.pause(2)
