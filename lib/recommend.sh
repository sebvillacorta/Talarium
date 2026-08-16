#!/usr/bin/env bash
# =============================================================================
# recommend.sh - Recomendaciones según el hardware y el sistema detectados
# =============================================================================

REC_ITEMS=()       # triples: tag | descripcion | on/off
RAM_GB=0

# ---------------------------------------------------------- construcción
build_recs() {
  REC_ITEMS=()
  RAM_GB=$(sys_mem_gb)
  local gpu
  gpu=$(sys_gpu_vendor)

  case "$PM" in
    dnf)
      if [[ ! -d /etc/yum.repos.d ]] || ! ls /etc/yum.repos.d/rpmfusion* >/dev/null 2>&1; then
        REC_ITEMS+=("fusion" "Habilitar repositorios RPM Fusion (codecs, drivers)" "off")
      fi
      if [[ "$HAVE_FLATPAK" == true ]] && ! flatpak remotes 2>/dev/null | grep -qi flathub; then
        REC_ITEMS+=("flathub" "Añadir el repositorio Flathub" "off")
      fi
      if ! is_installed ffmpeg; then
        REC_ITEMS+=("codecs" "Instalar codecs multimedia completos" "off")
      fi
      ;;
    pacman)
      if ! grep -q '^\[multilib\]' /etc/pacman.conf 2>/dev/null; then
        REC_ITEMS+=("multilib" "Habilitar repositorio multilib (Steam, 32 bits)" "off")
      fi
      if [[ -z "$AUR_HELPER" ]]; then
        REC_ITEMS+=("aur" "Instalar paru (asistente para el repositorio AUR)" "off")
      fi
      if ! is_installed ffmpeg; then
        REC_ITEMS+=("codecs" "Instalar codecs multimedia completos" "off")
      fi
      ;;
    apt)
      if ! grep -qE '^deb .*(contrib|non-free)' /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null; then
        REC_ITEMS+=("aptrepos" "Habilitar repositorios contrib y non-free" "off")
      fi
      if ! is_installed ffmpeg; then
        REC_ITEMS+=("codecs" "Instalar codecs multimedia completos" "off")
      fi
      ;;
  esac

  # Drivers de vídeo (S-Tier): NVIDIA requiere paquete propietario según distro.
  # AMD e Intel ya vienen integrados en el kernel gracias a Mesa.
  if [[ "$gpu" == "nvidia" ]]; then
    case "$PM" in
      dnf)    ! is_installed akmod-nvidia        && REC_ITEMS+=("nvidia"      "Instalar controladores NVIDIA (akmod-nvidia)" "off") ;;
      pacman) ! is_installed nvidia              && REC_ITEMS+=("nvidia-pm"   "Instalar controladores NVIDIA (nvidia)" "off") ;;
      apt)    ! is_installed nvidia-driver-535   && REC_ITEMS+=("nvidia-pm"   "Instalar controladores NVIDIA (nvidia-driver)" "off") ;;
      zypper) ! is_installed nvidia-driver-G06   && REC_ITEMS+=("nvidia-pm"   "Instalar controladores NVIDIA (nvidia-driver)" "off") ;;
    esac
  fi

  if [[ "$gpu" == "amd" ]]; then
    REC_ITEMS+=("amdgpu" "Verificar controladores AMD (Mesa usually sufficient)" "off")
  fi

  if is_systemd && sys_is_ssd && ! systemctl is-enabled fstrim.timer >/dev/null 2>&1; then
    REC_ITEMS+=("fstrim" "Activar TRIM automático para tu disco SSD" "off")
  fi

  if (( RAM_GB > 0 && RAM_GB <= 4 )); then
    REC_ITEMS+=("swap" "RAM baja: configurar zram/swap para mayor fluidez" "off")
  elif (( RAM_GB >= 16 )); then
    REC_ITEMS+=("performance" "Alta RAM: considerar desactivar swap para mejor rendimiento" "off")
  fi

  local cpu_cores
  cpu_cores=$(sys_cores 2>/dev/null || echo " desconocido")
  if [[ "$cpu_cores" -gt 4 ]]; then
    REC_ITEMS+=("build" "Equipo multicore: utilice compilación paralela para mejor rendimiento" "off")
  fi

  REC_ITEMS+=("update" "Actualizar todos los paquetes del sistema" "off")
}

# ---------------------------------------------------------- aplicación
run_rec() {
  case "$1" in
    fusion)
      ensure_sudo || return 1
      ui_info "Habilitando RPM Fusion"
      run_sudo dnf install -y \
        "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm" \
        "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm"
      ui_step "RPM Fusion habilitado."
      ;;
    flathub)
      ensure_sudo || return 1
      ui_info "Añadiendo Flathub"
      run_sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
      ui_step "Flathub añadido."
      ;;
    codecs)
      ensure_sudo || return 1
      ui_info "Instalando codecs multimedia"
      case "$PM" in
        dnf)
          run_sudo dnf group install -y multimedia
          run_sudo dnf config-manager setopt fedora-cisco-openh264.enabled=1 2>/dev/null || true
          run_pm PM_INSTALL gstreamer1-plugin-openh264 mozilla-openh264 || true
          ;;
        pacman)
          run_pm PM_INSTALL ffmpeg gst-plugins-good gst-plugins-bad gst-plugins-ugly
          ;;
        apt)
          run_pm PM_INSTALL ffmpeg gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
          ;;
      esac
      ui_step "Codecs instalados."
      ;;
    nvidia)
      ensure_sudo || return 1
      ui_info "Instalando controladores NVIDIA (akmod)"
      run_sudo dnf install -y akmod-nvidia xorg-x11-drv-nvidia-cuda
      ui_step "Controladores instalados. Reinicia para cargarlos (verifica con 'nvidia-smi')."
      ;;
    nvidia-pm)
      ensure_sudo || return 1
      ui_info "Instalando controladores NVIDIA"
      case "$PM" in
        pacman) run_pm PM_INSTALL nvidia ;;
        apt)    run_pm PM_INSTALL nvidia-driver-535 ;;
        zypper) run_pm PM_INSTALL nvidia-driver-G06 ;;
      esac
      ui_step "Controladores instalados. Reinicia para cargarlos (verifica con 'nvidia-smi')."
      ;;
    multilib)
      ensure_sudo || return 1
      ui_info "Habilitando multilib"
      run_sudo sed -i \
        -e 's/^#\[multilib\]/[multilib]/' \
        -e 's/^#Include = \/etc\/pacman.d\/mirrorlist/Include = \/etc\/pacman.d\/mirrorlist/' \
        /etc/pacman.conf
      run_sudo pacman -Sy --noconfirm
      ui_step "Multilib habilitado."
      ;;
    aur)
      ensure_sudo || return 1
      ui_info "Instalando paru desde AUR"
      command -v git >/dev/null 2>&1 || run_pm PM_INSTALL git
      rm -rf /tmp/talarium-paru
      git clone --depth=1 https://aur.archlinux.org/paru-bin.git /tmp/talarium-paru >/dev/null 2>&1 && (
        cd /tmp/talarium-paru || exit 1
        makepkg -si --noconfirm
      )
      detect_aur_helper
      if [[ -n "$AUR_HELPER" ]]; then
        ui_step "AUR helper '$AUR_HELPER' instalado."
      else
        ui_step "No se pudo instalar paru automáticamente."
      fi
      ;;
    aptrepos)
      ui_alert "Habilita los repositorios contrib y non-free editando\n/etc/apt/sources.list (o /etc/apt/sources.list.d/)\nañadiendo 'contrib non-free' a cada línea 'deb'.\n\nDespués ejecuta: sudo apt-get update"
      ;;
    fstrim)
      ensure_sudo || return 1
      run_sudo systemctl enable --now fstrim.timer
      ui_step "TRIM automático activado."
      ;;
    swap)
      case "$PM" in
        dnf)    cmd="sudo dnf install -y zram-generator" ;;
        pacman) cmd="sudo pacman -S --noconfirm zram-generator" ;;
        apt)    cmd="sudo apt-get install -y zram-tools" ;;
        *)      cmd="" ;;
      esac
      if [[ -n "$cmd" ]]; then
        ui_alert "Tu equipo tiene ${RAM_GB} GB de RAM.\nRecomendación: compresión en RAM (zram).\n\nComando sugerido:\n${cmd}"
      else
        ui_alert "Tu equipo tiene ${RAM_GB} GB de RAM.\nConsidera ampliar swap o usar zram."
      fi
      ;;
    update)
      run_update_system
      ;;
    performance)
      ui_info "Tu equipo tiene ${RAM_GB} GB de RAM y $(sys_cores) núcleos de CPU."
      ui_step "Considera desactivar swap si tienes suficiente RAM para mejorar el rendimiento del sistema."
      ;;
  esac
}

# ---------------------------------------------------------- menú
menu_recomendaciones() {
  set_backtitle tips
  build_recs

  local info
  info="RAM: ${RAM_GB} GB | CPU: $(sys_cores) núcleos | GPU: $(sys_gpu_vendor) | Disco: $(sys_is_ssd && echo SSD || echo HDD)"

  if ((${#REC_ITEMS[@]} == 0)); then
    ui_alert "No hay recomendaciones para este equipo.\n\n$info"
    return
  fi

  local sel
  sel=$(ui_checklist "Recomendaciones" "$info
Marca con ESPACIO las que quieras aplicar" "${REC_ITEMS[@]}") || return
  [[ -n "$sel" ]] || { ui_alert "No seleccionaste ninguna recomendación."; return; }

  ui_yesno "Aplicar recomendaciones" "Se aplicarán:\n${sel}" || return

  local r
  for r in $sel; do
    run_rec "$r"
  done
  ui_pause
}
