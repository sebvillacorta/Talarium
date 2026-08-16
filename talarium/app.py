"""Aplicación principal de Talarium: ciclo de vida de la sesión.

Responsabilidades:
- Orquestar la detección (distro, UI, gestor) en 'bootstrap'.
- Construir el Context con todos los servicios inyectados.
- Mostrar el banner de bienvenida.
- Bucle del menú principal y despido.
- Instalar manejadores de señal para limpiar la sesión sudo al salir.

Las funciones de los módulos se importan de forma perezosa para evitar
importaciones circulares (módulos <-> contexto).
"""

import shutil
import sys

from . import __version__
from .context import Context
from .core.catalog import Catalog
from .core.packagemanager import factory as pm_factory
from .core.runner import Runner
from .core.system import detect_distro, require_supported
from .errors import UserExit
from .sudo import SudoSession, install_signal_cleanup
from .ui import create_ui
from .ui.banner import BANNER, FOOTER


class TalariumApp:
    def __init__(self, ui_force: str = "") -> None:
        self.ui_force = ui_force
        self.ctx: Context | None = None

    # ------------------------------------------------------------ bootstrap
    def bootstrap(self) -> None:
        distro = detect_distro()
        require_supported(distro)

        ui = create_ui(force=self.ui_force or None,
                       rcfile=str(self._theme_file()))
        sudo = SudoSession(ui=ui)
        install_signal_cleanup(sudo)
        runner = Runner(sudo)
        catalog = Catalog()
        pm = pm_factory(runner, distro.pm)
        from .core.packagemanager import Flatpak
        flatpak = Flatpak(runner, distro.has_flatpak)

        self.ctx = Context(distro=distro, ui=ui, sudo=sudo, runner=runner,
                           catalog=catalog, pm=pm, flatpak=flatpak)
        ui.set_backtitle()

    @staticmethod
    def _theme_file():
        from .config import THEME_FILE
        return THEME_FILE

    # -------------------------------------------------------------- banner
    def welcome(self) -> None:
        if not sys.stdout.isatty():
            return
        print(BANNER)
        print(FOOTER)
        print()
        try:
            key = input("  Enter o S = continuar   ·   N o Esc = cancelar: ")
        except (EOFError, KeyboardInterrupt):
            raise SystemExit(0)
        if key.strip().lower() in ("n", "no"):
            raise SystemExit(0)

    def maybe_upgrade_ui(self) -> None:
        """Si sólo hay texto, ofrece instalar dialog para mejor experiencia."""
        ui = self.ctx.ui
        if ui.name in ("texto",):
            self.ctx.ui.set_backtitle("")
            if self.ctx.ui.yesno("Interfaz", "Instalar 'dialog' para una interfaz más completa y bonita?"):
                try:
                    self.ctx.sudo.ensure()
                    self.ctx.pm.install(["dialog"])
                except Exception as exc:  # noqa: BLE001 - error no fatal
                    print(f"  No se pudo instalar dialog: {exc}")
                ui = create_ui(rcfile=str(self._theme_file()))
                self.ctx.ui = ui
                ui.set_backtitle("")

    # ------------------------------------------------------------ main loop
    def run(self) -> int:
        self.bootstrap()
        self.welcome()
        self.maybe_upgrade_ui()

        ctx = self.ctx
        while True:
            ui = ctx.ui
            ui.set_backtitle("")
            sel = ui.menu(
                "Talarium - Panel principal",
                f"Sistema: {ctx.distro.name} {ctx.distro.version} | "
                f"Escritorio: {ctx.distro.de_name} | Gestor: {ctx.distro.pm}",
                [
                    ("soft", "Software: instalar / desinstalar aplicaciones"),
                    ("sys", "Sistema: limpieza, desbloat y mantenimiento"),
                    ("visual", "Visual: ajustes gráficos e interfaz"),
                    ("tips", "Consejos: recomendaciones según tu equipo"),
                    ("backup", "Copia de seguridad y restauración"),
                    ("help", "Ayuda e información"),
                    ("exit", "Salir"),
                ],
            )
            if sel is None:
                break
            try:
                if sel == "soft":
                    from .modules.software import menu_software
                    menu_software(ctx)
                elif sel == "sys":
                    from .modules.maintenance import menu_sistema
                    menu_sistema(ctx)
                elif sel == "visual":
                    from .modules.visual import menu_visual
                    menu_visual(ctx)
                elif sel == "tips":
                    from .modules.recommend import menu_recomendaciones
                    menu_recomendaciones(ctx)
                elif sel == "backup":
                    from .modules.backup import menu_backup
                    menu_backup(ctx)
                elif sel == "help":
                    self.help_screen(ctx)
            except UserExit:
                break
            except Exception as exc:  # noqa: BLE001 - error mostrado al usuario
                ctx.ui.alert("Error", str(exc) or exc.__class__.__name__)
        self.farewell()
        return 0

    # --------------------------------------------------------------- extras
    def help_screen(self, ctx: Context) -> None:
        ctx.ui.set_backtitle("help")
        ctx.ui.alert(
            "Ayuda",
            f"Talarium v{__version__} - Gestor de sistema para Linux\n"
            "  1. Software  -> instalar/desinstalar por categorías\n"
            "  2. Sistema   -> desbloat, huérfanos, cachés, journal, actualizar\n"
            "  3. Visual    -> ajustes gráficos (GNOME/KDE/XFCE), fuentes, zsh, TRIM\n"
            "  4. Consejos  -> recomendaciones según tu hardware y distro\n"
            "  5. Backup    -> copia de seguridad y restauración\n\n"
            "Seguridad:\n"
            "  Nada se instala ni elimina sin tu confirmación.\n"
            "  La contraseña de sudo se pide una sola vez por sesión,\n"
            "  se guarda sólo en memoria y se borra al salir (sudo -k).\n\n"
            "Más opciones:\n"
            "  talarium --doctor     Diagnóstico del sistema\n"
            "  talarium --help       Ayuda",
        )

    @staticmethod
    def farewell() -> None:
        if sys.stdout.isatty():
            print("\n  ¡Hasta pronto! La sesión de sudo se ha cerrado.\n")


# =================================================================== doctor
def run_doctor() -> int:
    """Diagnóstico del sistema (sin interfaz gráfica)."""
    from .core.system import detect_distro, mem_gb, cores, gpu_vendor, is_ssd, is_systemd
    from .config import BACKUP_BASE
    from .core.catalog import Catalog

    d = detect_distro()
    catalog = Catalog()
    print("==================  Talarium - Diagnóstico  ==================")
    print(f"  Distro          : {d.name} ({d.id}) {d.version}")
    print(f"  Gestor de paq.  : {d.pm or 'NO SOPORTADO'}")
    print(f"  Escritorio      : {d.de_name}")
    print(f"  Interfaz        : {create_ui(rcfile=str(catalog.config_dir / 'theme' / 'dialog.mono')).name}")
    print(f"  AUR helper      : {d.aur_helper or 'ninguno'}")
    print(f"  Flatpak         : {'disponible' if d.has_flatpak else 'no'}")
    print(f"  Root            : {'sí' if d.is_root else 'no'} | Sudo: {'sí' if d.has_sudo else 'no'}")
    print(f"  RAM             : {mem_gb()} GB | CPU: {cores()} núcleos | GPU: {gpu_vendor()}")
    print(f"  Disco           : {'SSD' if is_ssd() else 'HDD'} | systemd: {'sí' if is_systemd() else 'no'}")
    print(f"  Backups         : {BACKUP_BASE}")
    try:
        print(f"  Config software : {', '.join(p.name for p in sorted((catalog.config_dir / 'software').glob('*.conf')))}")
        print(f"  Config debloat  : {', '.join(p.name for p in sorted((catalog.config_dir / 'debloat').glob('*.conf')))}")
    except OSError:
        pass
    print("===============================================================")
    if not d.pm:
        print("\n  ADVERTENCIA: tu distro no está soportada todavía.")
        print("  Gestores soportados: dnf, pacman, apt, zypper, xbps.")
        return 1
    return 0


def ensure_dialog_hint() -> None:
    if shutil.which("dialog") is None and sys.stdout.isatty():
        print("\n  Sugerencia: instala 'dialog' para la interfaz completa.")
        print("  (Talarium seguirá funcionando con whiptail o texto.)\n")
