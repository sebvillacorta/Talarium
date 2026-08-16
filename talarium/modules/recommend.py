"""Consejos: recomendaciones según hardware y distribución.

build_recs() inspecciona el sistema y propone acciones opcionales:
repositorios (RPM Fusion / multilib / contrib-non-free), Flathub,
codecs, controladores NVIDIA, TRIM, swap/zram, etc.
Cada acción se aplica con confirmación y con sudo validado.
"""

from pathlib import Path


from ..context import Context
from ..core.system import cores, gpu_vendor, is_systemd, is_ssd, mem_gb
from ..errors import CommandError
from .common import confirm_and_run, operation_completed


def build_recs(ctx: Context) -> list:
    """Devuelve [(tag, etiqueta, marcado)] según el sistema detectado."""
    d, pm = ctx.distro, ctx.pm
    recs = []
    gpu = gpu_vendor()

    if pm.name == "dnf":
        if not any(Path("/etc/yum.repos.d").glob("rpmfusion*")):
            recs.append(("fusion", "Habilitar repositorios RPM Fusion (codecs, drivers)", False))
        if d.has_flatpak and not _has_flathub(ctx):
            recs.append(("flathub", "Añadir el repositorio Flathub", False))
        if not pm.is_installed("ffmpeg"):
            recs.append(("codecs", "Instalar codecs multimedia completos", False))

    elif pm.name == "pacman":
        if not _grep("/etc/pacman.conf", r"^\[multilib\]"):
            recs.append(("multilib", "Habilitar repositorio multilib (Steam, 32 bits)", False))
        if not d.aur_helper:
            recs.append(("aur", "Instalar paru (asistente para el repositorio AUR)", False))
        if not pm.is_installed("ffmpeg"):
            recs.append(("codecs", "Instalar codecs multimedia completos", False))

    elif pm.name == "apt":
        if not _grep(("/etc/apt/sources.list", *Path("/etc/apt/sources.list.d").glob("*")),
                     r"^deb .*(contrib|non-free)"):
            recs.append(("aptrepos", "Habilitar repositorios contrib y non-free", False))
        if not pm.is_installed("ffmpeg"):
            recs.append(("codecs", "Instalar codecs multimedia completos", False))

    if gpu == "nvidia":
        target = {"dnf": "akmod-nvidia", "pacman": "nvidia",
                  "apt": "nvidia-driver-535", "zypper": "nvidia-driver-G06"}.get(pm.name)
        if target and not pm.is_installed(target):
            recs.append(("nvidia", "Instalar controladores NVIDIA", False))
    elif gpu == "amd":
        recs.append(("amdgpu", "Verificar controladores AMD (Mesa suele bastar)", False))

    if is_systemd() and is_ssd() and not _fstrim_enabled():
        recs.append(("fstrim", "Activar TRIM automático para tu disco SSD", False))

    ram = mem_gb()
    if 0 < ram <= 4:
        recs.append(("swap", "RAM baja: configurar zram/swap para mayor fluidez", False))
    elif ram >= 16:
        recs.append(("performance", "Alta RAM: considerar desactivar swap para mejor rendimiento", False))

    if cores() > 4:
        recs.append(("build", "Equipo multicore: usa compilación paralela (makepkg -j, ninja -j)", False))

    recs.append(("update", "Actualizar todos los paquetes del sistema", False))
    return recs


def _has_flathub(ctx: Context) -> bool:
    out = ctx.runner.check_output(["flatpak", "remotes"], timeout=30).lower()
    return "flathub" in out


def _grep(paths, pattern) -> bool:
    import re
    if isinstance(paths, str):
        paths = [paths]
    for p in paths:
        try:
            if re.search(pattern, Path(p).read_text(errors="replace"), re.M):
                return True
        except OSError:
            continue
    return False


def _fstrim_enabled() -> bool:
    try:
        import subprocess
        proc = subprocess.run(["systemctl", "is-enabled", "fstrim.timer"],
                              capture_output=True, text=True)
        return proc.returncode == 0 and proc.stdout.strip() == "enabled"
    except OSError:
        return False


# ------------------------------------------------------------------ aplicar
def menu_recomendaciones(ctx: Context) -> None:
    ui = ctx.ui
    ui.set_backtitle("tips")
    recs = build_recs(ctx)
    info = f"RAM: {mem_gb()} GB | CPU: {cores()} núcleos | GPU: {gpu_vendor()} | Disco: {'SSD' if is_ssd() else 'HDD'}"

    if not recs:
        ui.alert("Recomendaciones", f"No hay recomendaciones para este equipo.\n\n{info}")
        return

    chosen = ui.checklist("Recomendaciones", info + "\nMarca con ESPACIO las que quieras aplicar", recs)
    if not chosen:
        ui.alert("Recomendaciones", "No seleccionaste ninguna recomendación.")
        return

    if ui.yesno("Aplicar recomendaciones", f"Se aplicarán:\n{' '.join(chosen)}"):
        for tag in chosen:
            _apply(ctx, tag)
        operation_completed(ctx, "Operación completada",
                            f"Recomendaciones aplicadas:\n{' '.join(chosen)}")


def _apply(ctx: Context, tag: str) -> None:
    d, ui = ctx.distro, ctx.ui
    pm = ctx.pm

    if tag == "fusion":
        import subprocess
        fedora = "44"
        try:
            fedora = subprocess.run(["rpm", "-E", "%fedora"], capture_output=True,
                                    text=True).stdout.strip() or fedora
        except OSError:
            pass
        confirm_and_run(ctx, "RPM Fusion", "Habilitar repositorios RPM Fusion (free + nonfree)?",
                        lambda: ctx.runner.priv([
                            "dnf", "install", "-y",
                            f"https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-{fedora}.noarch.rpm",
                            f"https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-{fedora}.noarch.rpm",
                        ], timeout=900), "Habilitando RPM Fusion...")

    elif tag == "flathub":
        confirm_and_run(ctx, "Flathub", "Añadir el repositorio Flathub?",
                        lambda: ctx.flatpak.ensure_flathub(), "Añadiendo Flathub...")

    elif tag == "codecs":
        map_pm = {
            "dnf": [["dnf", "group", "install", "-y", "multimedia"],
                    ["dnf", "install", "-y", "gstreamer1-plugin-openh264", "mozilla-openh264"]],
            "pacman": [pm.install_cmd + ["ffmpeg", "gst-plugins-good", "gst-plugins-bad", "gst-plugins-ugly"]],
            "apt": [pm.install_cmd + ["ffmpeg", "gstreamer1.0-plugins-good",
                                      "gstreamer1.0-plugins-bad", "gstreamer1.0-plugins-ugly"]],
        }
        cmds = map_pm.get(pm.name)
        if not cmds:
            ui.alert("Codecs", f"Codecs no definidos para el gestor '{pm.name}'.")
            return
        confirm_and_run(ctx, "Codecs", "Instalar codecs multimedia completos?",
                        lambda: [ctx.runner.priv(c, timeout=1800) for c in cmds],
                        "Instalando codecs...")

    elif tag == "nvidia":
        cmds = {
            "dnf": [["dnf", "install", "-y", "akmod-nvidia", "xorg-x11-drv-nvidia-cuda"]],
            "pacman": [pm.install_cmd + ["nvidia"]],
            "apt": [pm.install_cmd + ["nvidia-driver-535"]],
            "zypper": [pm.install_cmd + ["nvidia-driver-G06"]],
        }.get(pm.name)
        if not cmds:
            ui.alert("NVIDIA", f"Controladores no definidos para '{pm.name}'.")
            return
        confirm_and_run(ctx, "NVIDIA", "Instalar controladores NVIDIA?\nReinicia tras instalar.",
                        lambda: [ctx.runner.priv(c, timeout=1800) for c in cmds],
                        "Instalando controladores NVIDIA...")

    elif tag == "multilib":
        def _multilib():
            pac = "/etc/pacman.conf"
            text = Path(pac).read_text()
            text = text.replace("#[multilib]", "[multilib]")
            text = text.replace("#Include = /etc/pacman.d/mirrorlist", "Include = /etc/pacman.d/mirrorlist")
            Path(pac).write_text(text)
            ctx.runner.priv(["pacman", "-Sy", "--noconfirm"], timeout=1800)
        confirm_and_run(ctx, "Multilib", "Habilitar el repositorio multilib de Arch?",
                        _multilib, "Habilitando multilib...")

    elif tag == "aur":
        def _install_paru():
            import shutil
            import subprocess
            tmp = Path("/tmp/talarium-paru")
            if tmp.exists():
                shutil.rmtree(tmp)
            ctx.runner.run(["git", "clone", "--depth=1",
                            "https://aur.archlinux.org/paru-bin.git", str(tmp)], timeout=300)
            proc = subprocess.run(["makepkg", "-si", "--noconfirm"], cwd=str(tmp),
                                  timeout=3600)
            if proc.returncode != 0:
                raise CommandError("Fallo al compilar paru con makepkg.")
            from ..core.system import detect_distro
            ctx.distro.aur_helper = detect_distro().aur_helper
        confirm_and_run(ctx, "AUR", "Instalar paru (helper AUR) compilando desde AUR?",
                        _install_paru, "Instalando paru...")

    elif tag == "aptrepos":
        ui.alert("Repositorios",
                 "Habilita los repositorios contrib y non-free editando\n"
                 "/etc/apt/sources.list (o /etc/apt/sources.list.d/)\n"
                 "añadiendo 'contrib non-free' a cada línea 'deb'.\n\n"
                 "Después ejecuta: sudo apt-get update")

    elif tag == "fstrim":
        confirm_and_run(ctx, "TRIM", "Activar TRIM automático (fstrim.timer)?",
                        lambda: ctx.runner.priv(["systemctl", "enable", "--now", "fstrim.timer"], timeout=120),
                        "Activando TRIM...")

    elif tag == "swap":
        cmd = {"dnf": "sudo dnf install -y zram-generator",
               "pacman": "sudo pacman -S --noconfirm zram-generator",
               "apt": "sudo apt-get install -y zram-tools"}.get(pm.name)
        ram = mem_gb()
        if cmd:
            ui.alert("Swap", f"Tu equipo tiene {ram} GB de RAM.\n"
                             "Recomendación: compresión en RAM (zram).\n\n"
                             f"Comando sugerido:\n{cmd}")
        else:
            ui.alert("Swap", f"Tu equipo tiene {ram} GB de RAM.\n"
                             "Considera ampliar swap o usar zram.")

    elif tag == "performance":
        ui.alert("Rendimiento",
                 f"Tu equipo tiene {mem_gb()} GB de RAM y {cores()} núcleos.\n"
                 "Considera desactivar swap si tienes suficiente RAM para mejorar "
                 "la fluidez del sistema.")

    elif tag == "build":
        ui.alert("Compilación",
                 "Tu equipo tiene varios núcleos. Configura compilación paralela:\n"
                 "  Arch:  MAKEFLAGS=\"-j$(nproc)\"  en /etc/makepkg.conf\n"
                 "  Ninja/CMake:  ninja -j$(nproc)  o  cmake --build . -j$(nproc)")

    elif tag == "update":
        from .maintenance import run_update_system
        run_update_system(ctx)

    elif tag == "amdgpu":
        ui.alert("AMD", "Tu GPU AMD usa el controlador open source 'amdgpu' del kernel.\n"
                        "No suele requerir instalación adicional. Verifica con 'vulkaninfo' o 'glxinfo'.")
