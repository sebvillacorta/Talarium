"""Visual: ajustes gráficos e interfaz (GNOME / KDE / XFCE), fuentes, zsh, TRIM."""

import shutil
import subprocess
from pathlib import Path

from ..context import Context
from ..core.system import is_systemd, is_ssd
from ..errors import CommandError, SudoError
from .common import ensure_sudo


def menu_visual(ctx: Context) -> None:
    ui = ctx.ui
    ui.set_backtitle("visual")
    sel = ui.menu("Visual - apariencia y rendimiento",
                  f"Escritorio detectado: {ctx.distro.de_name}",
                  [("de", "Ajustes del escritorio actual"),
                   ("fonts", "Instalar fuentes de programación (JetBrains Mono, Fira Code)"),
                   ("zsh", "Instalar Zsh + Oh My Zsh (mejor terminal)"),
                   ("ssd", "Activar TRIM automático para SSD (fstrim)"),
                   ("back", "Volver al menú principal")])
    if sel == "de":
        _de_tweaks(ctx)
    elif sel == "fonts":
        fonts(ctx)
    elif sel == "zsh":
        zsh_setup(ctx)
    elif sel == "ssd":
        ssd_trim(ctx)


# ----------------------------------------------------------------- escritorio
def _de_tweaks(ctx: Context) -> None:
    if ctx.distro.de == "gnome":
        _gnome(ctx)
    elif ctx.distro.de == "kde":
        _kde(ctx)
    elif ctx.distro.de == "xfce":
        _xfce(ctx)
    else:
        ctx.ui.alert("Visual", f"El escritorio {ctx.distro.de_name} aún no tiene ajustes específicos definidos.")


def _gnome(ctx: Context) -> None:
    if shutil.which("gsettings") is None:
        ctx.ui.alert("GNOME", "gsettings no está disponible en este sistema.")
        return
    sel = ctx.ui.menu("Ajustes GNOME", "",
                      [("dark", "Modo oscuro (tema y aplicaciones)"),
                       ("btns", "Mostrar botones minimizar/maximizar en ventanas"),
                       ("tap", "Activar 'tocar para hacer clic' en el touchpad"),
                       ("night", "Activar luz nocturna (pantalla cálida al anochecer)"),
                       ("anim", "Desactivar animaciones (respuesta más rápida)"),
                       ("week", "Mostrar números de semana en el calendario"),
                       ("back", "Volver")])
    gs = ["gsettings", "set"]
    sets = {
        "dark": [["org.gnome.desktop.interface", "color-scheme", "prefer-dark"],
                 ["org.gnome.desktop.interface", "gtk-theme", "Adwaita-dark"]],
        "btns": [["org.gnome.desktop.wm.preferences", "button-layout", "appmenu:minimize,maximize,close"]],
        "tap": [["org.gnome.desktop.peripherals.touchpad", "tap-to-click", "true"]],
        "night": [["org.gnome.settings-daemon.plugins.color", "night-light-enabled", "true"],
                  ["org.gnome.settings-daemon.plugins.color", "night-light-schedule-automatic", "true"]],
        "anim": [["org.gnome.desktop.interface", "enable-animations", "false"]],
        "week": [["org.gnome.desktop.calendar", "show-weekdate", "true"]],
    }
    if sel in sets:
        for s in sets[sel]:
            subprocess.run(gs + s, capture_output=True)
        ctx.ui.step(f"Ajuste '{sel}' aplicado.")
        ctx.ui.pause(2)


def _kde(ctx: Context) -> None:
    sel = ctx.ui.menu("Ajustes KDE Plasma", "",
                      [("dark", "Tema oscuro BreezeDark"),
                       ("back", "Volver")])
    if sel == "dark":
        if shutil.which("plasma-apply-colorscheme"):
            subprocess.run(["plasma-apply-colorscheme", "BreezeDark"], capture_output=True)
            ctx.ui.step("Tema BreezeDark aplicado.")
        else:
            kc = shutil.which("kwriteconfig6") or shutil.which("kwriteconfig5")
            if kc:
                subprocess.run([kc, "--file", "kdeglobals", "--group", "General",
                                "--key", "ColorScheme", "BreezeDark"], capture_output=True)
                ctx.ui.step("Color configurado. Reinicia sesión para ver el cambio.")
            else:
                ctx.ui.alert("KDE", "No se encontró kwriteconfig ni plasma-apply-colorscheme.")
        ctx.ui.pause(2)


def _xfce(ctx: Context) -> None:
    if shutil.which("xfconf-query"):
        subprocess.run(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName",
                        "-s", "Adwaita-dark"], capture_output=True)
        ctx.ui.step("Tema Adwaita-dark aplicado.")
    else:
        ctx.ui.alert("XFCE", "xfconf no está disponible.")
    ctx.ui.pause(2)


# -------------------------------------------------------------------- fuentes
def fonts(ctx: Context) -> None:
    pkgs = ctx.pm.font_packages()
    if not pkgs:
        ctx.ui.alert("Visual", f"Fuentes no definidas para el gestor '{ctx.distro.pm}'.")
        return
    if not ensure_sudo(ctx):
        return
    try:
        ctx.pm.install(pkgs)
        ctx.ui.step("JetBrains Mono y Fira Code instaladas.")
    except (SudoError, CommandError) as exc:
        ctx.ui.alert("Fuentes", str(exc))
    ctx.ui.pause(2)


# ------------------------------------------------------------------------ zsh
def zsh_setup(ctx: Context) -> None:
    ui = ctx.ui
    if not ensure_sudo(ctx):
        return
    try:
        if shutil.which("zsh") is None:
            ui.step("Instalando Zsh...")
            ctx.pm.install([ctx.pm.zsh_package()])

        oh_my = Path.home() / ".oh-my-zsh"
        if not oh_my.is_dir():
            if shutil.which("git"):
                import urllib.request
                ui.step("Descargando Oh My Zsh...")
                ok = False
                if shutil.which("curl"):
                    script = "https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh"
                    proc = subprocess.run(["bash", "-c",
                                           f"RUNZSH=no CHSH=no bash -c \"$(curl -fsSL {script})\" \"\" --unattended"],
                                          capture_output=True, timeout=300)
                    ok = proc.returncode == 0
                if not ok and not oh_my.is_dir():
                    subprocess.run(["git", "clone", "--depth=1",
                                    "https://github.com/ohmyzsh/ohmyzsh.git", str(oh_my)],
                                   capture_output=True, timeout=300)
                if not (Path.home() / ".zshrc").exists() and (oh_my / "templates" / "zshrc.zsh-template").is_file():
                    import shutil as _sh
                    _sh.copy(str(oh_my / "templates" / "zshrc.zsh-template"), str(Path.home() / ".zshrc"))
                ui.step("Oh My Zsh instalado.")
            else:
                ui.alert("Zsh", "Se necesita 'git' para instalar Oh My Zsh.")
    except (SudoError, CommandError) as exc:
        ui.alert("Zsh", str(exc))
        return

    zsh_path = shutil.which("zsh")
    import os
    if zsh_path and os.environ.get("SHELL") != zsh_path:
        if ui.yesno("Shell por defecto", "¿Usar zsh como shell predeterminada?"):
            try:
                subprocess.run(["chsh", "-s", zsh_path], capture_output=True)
                ui.step("Shell cambiada (se aplica al reabrir la terminal).")
            except OSError:
                ui.alert("Zsh", "No se pudo cambiar la shell.")
    ui.pause(2)


# ----------------------------------------------------------------------- ssd
def ssd_trim(ctx: Context) -> None:
    if not is_ssd():
        ctx.ui.alert("TRIM", "No se detectó un disco SSD. TRIM no es necesario.")
        return
    if not is_systemd():
        ctx.ui.alert("TRIM", "Este sistema no usa systemd (fstrim.timer no aplica).")
        return
    if not ensure_sudo(ctx):
        return
    try:
        ctx.runner.priv(["systemctl", "enable", "--now", "fstrim.timer"], timeout=120)
        ctx.ui.step("TRIM automático activado (fstrim.timer).")
    except (SudoError, CommandError) as exc:
        ctx.ui.alert("TRIM", f"No se pudo activar fstrim.timer:\n{exc}")
    ctx.ui.pause(2)
