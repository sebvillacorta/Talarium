"""Helpers compartidos por los módulos: sudo seguro y operaciones con aviso."""

from typing import Callable, List, Sequence, TypeVar

from ..context import Context
from ..errors import CommandError, SudoError, UserExit

T = TypeVar("T")


def ensure_sudo(ctx: Context) -> bool:
    """Valida la sesión sudo (pide contraseña si hace falta) y avisa si falla."""
    try:
        return ctx.sudo.ensure()
    except SudoError as exc:
        ctx.ui.alert("Permisos", str(exc))
        return False


def run_privileged(ctx: Context, fn: Callable[[], T]) -> T | None:
    """Ejecuta fn con sudo ya validado; muestra el error sin abortar la sesión."""
    if not ensure_sudo(ctx):
        return None
    try:
        return fn()
    except (SudoError, CommandError) as exc:
        ctx.ui.alert("Error", str(exc))
        return None
    except Exception as exc:  # noqa: BLE001 - el resto se informa igualmente
        ctx.ui.alert("Error", f"{exc.__class__.__name__}: {exc}")
        return None


def split_packages(pkgs: Sequence[str]) -> tuple:
    """Separa una lista de paquetes en (nativos, aur, flatpak)."""
    native: List[str] = []
    aur: List[str] = []
    flat: List[str] = []
    for p in pkgs:
        if p.startswith("aur:"):
            aur.append(p[len("aur:"):])
        elif p.startswith("flatpak:"):
            flat.append(p[len("flatpak:"):])
        else:
            native.append(p)
    return native, aur, flat


def install_packages(ctx: Context, pkgs: Sequence[str]) -> bool:
    """Instala paquetes mixtos (nativo + AUR + Flatpak) con confirmación previa."""
    native, aur, flat = split_packages(pkgs)
    ok = True
    if native:
        print(f">> Instalando: {' '.join(native)}")
        ok = run_privileged(ctx, lambda: ctx.pm.install(native)) is not None and ok
    if aur:
        if not ctx.distro.aur_helper:
            ctx.ui.alert("AUR", "No se encontró paru/yay para los paquetes AUR.\n"
                                 "Puedes instalarlo desde 'Consejos'.")
            ok = False
        else:
            print(f">> Instalando (AUR): {' '.join(aur)}")
            cmd = [ctx.distro.aur_helper, "-S", "--noconfirm", "--needed"] + aur
            ok = run_privileged(ctx, lambda: ctx.runner.priv(cmd, timeout=3600)) is not None and ok
    if flat:
        ok = run_privileged(ctx, lambda: ctx.flatpak.install(flat)) is not None and ok
    return ok


def remove_packages(ctx: Context, pkgs: Sequence[str]) -> bool:
    """Elimina paquetes mixtos (nativo + Flatpak)."""
    native, aur, flat = split_packages(pkgs)
    ok = True
    if native:
        print(f">> Eliminando: {' '.join(native)}")
        ok = run_privileged(ctx, lambda: ctx.pm.remove(native)) is not None and ok
    if flat:
        ok = run_privileged(ctx, lambda: ctx.flatpak.remove(flat)) is not None and ok
    return ok


def confirm_and_run(ctx: Context, title: str, text: str,
                    fn: Callable[[], T], run_msg: str) -> None:
    """Patrón común: confirmar -> ejecutar con sudo -> pausa."""
    if not ctx.ui.yesno(title, text):
        return
    if not ensure_sudo(ctx):
        return
    ctx.ui.step(run_msg)
    try:
        fn()
    except (SudoError, CommandError) as exc:
        ctx.ui.alert("Error", str(exc))
    ctx.ui.pause(2)


def operation_completed(ctx: Context, title: str = "Instalación completada",
                        message: str = "La operación finalizó correctamente.") -> None:
    """Aviso de operación terminada con opción de volver al menú o salir.

    Si el usuario elige "Salir", se lanza UserExit para que el bucle
    principal de la aplicación termine de forma controlada.
    """
    sel = ctx.ui.menu(title, message,
                      [("menu", "Regresar al menú principal"),
                       ("exit", "Salir del programa")])
    if sel == "exit":
        raise UserExit()
