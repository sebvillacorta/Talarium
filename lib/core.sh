#!/usr/bin/env bash
# =============================================================================
# core.sh - Detección de sistema y abstracción de gestores de paquetes
# Parte de Talarium, gestor de sistema creado por sebvillacorta (alias RevOst)
# =============================================================================

# ---------------------------------------------------------------- variables
DISTRO_ID=""
DISTRO_NAME=""
DISTRO_VERSION=""
PM=""                       # dnf | pacman | apt | zypper | xbps | apk
PM_INSTALL=()               # comando base para instalar (sin paquetes)
PM_REMOVE=()
PM_UPDATE=()
PM_UPGRADE=()
PM_AUTOREMOVE=()
PM_CLEAN=()
PM_SEARCH=()
PM_QUERY=()
DE="other"                  # gnome | kde | xfce | cinnamon | mate | other
AUR_HELPER=""               # paru | yay | ""
IS_ROOT=false
HAVE_SUDO=false
HAVE_FLATPAK=false
INTERACTIVE=false

# ============================================================ detección distro
detect_distro() {
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    DISTRO_ID="${ID:-unknown}"
    DISTRO_NAME="${NAME:-$DISTRO_ID}"
    DISTRO_VERSION="${VERSION_ID:-?}"
  else
    DISTRO_ID="unknown"; DISTRO_NAME="desconocida"; DISTRO_VERSION="?"
  fi

  case "$DISTRO_ID" in
    fedora|rhel|centos|rocky|almalinux|nobara|blackrhino)
      PM="dnf" ;;
    arch|manjaro|endeavouros|garuda|arcolinux|artix|archcraft|cachyos|endes)
      PM="pacman" ;;
    debian|ubuntu|linuxmint|pop|elementary|zorin|kali|mx|linux-sl)
      PM="apt" ;;
    opensuse*|suse|sled|sles|opensuse-tm)
      PM="zypper" ;;
    void)  PM="xbps" ;;
    alpine) PM="apk" ;;
    *)     PM="" ;;
  esac

  set_pm_commands
  detect_aur_helper
  check_env
}

# ======================================================= comandos por gestor
set_pm_commands() {
  case "$PM" in
    dnf)
      PM_INSTALL=(dnf install -y --skip-broken)
      PM_REMOVE=(dnf remove -y)
      PM_UPDATE=(dnf check-update)
      PM_UPGRADE=(dnf upgrade -y)
      PM_AUTOREMOVE=(dnf autoremove -y)
      PM_CLEAN=(dnf clean all)
      PM_SEARCH=(dnf search)
      PM_QUERY=(rpm -q)
      ;;
    pacman)
      PM_INSTALL=(pacman -S --noconfirm --needed)
      PM_REMOVE=(pacman -Rns --noconfirm)
      PM_UPDATE=(pacman -Sy)
      PM_UPGRADE=(pacman -Syu --noconfirm)
      PM_AUTOREMOVE=(pacman -Rns --noconfirm)
      PM_CLEAN=(pacman -Scc --noconfirm)
      PM_SEARCH=(pacman -Ss)
      PM_QUERY=(pacman -Q)
      ;;
    apt)
      PM_INSTALL=(apt-get install -y)
      PM_REMOVE=(apt-get purge -y)
      PM_UPDATE=(apt-get update)
      PM_UPGRADE=(apt-get upgrade -y)
      PM_AUTOREMOVE=(apt-get autoremove -y --purge)
      PM_CLEAN=(apt-get clean)
      PM_SEARCH=(apt-cache search)
      PM_QUERY=(dpkg -s)
      ;;
    zypper)
      PM_INSTALL=(zypper install -y)
      PM_REMOVE=(zypper remove -y)
      PM_UPDATE=(zypper refresh)
      PM_UPGRADE=(zypper update -y)
      PM_AUTOREMOVE=(zypper remove -y --clean-deps)
      PM_CLEAN=(zypper clean -a)
      PM_SEARCH=(zypper search)
      PM_QUERY=(rpm -q)
      ;;
    xbps)
      PM_INSTALL=(xbps-install -y)
      PM_REMOVE=(xbps-remove -y -R)
      PM_UPDATE=(xbps-install -Sy)
      PM_UPGRADE=(xbps-install -Su)
      PM_AUTOREMOVE=(xbps-remove -yo)
      PM_CLEAN=(xbps-remove -O)
      PM_SEARCH=(xbps-query -Rs)
      PM_QUERY=(xbps-query)
      ;;
  esac
}

# ============================================================ detección del DE
detect_de() {
  DE="other"
  local xdg="${XDG_CURRENT_DESKTOP,,}"
  case "$xdg" in
    *gnome*)    DE="gnome" ;;
    *kde*|*plasma*) DE="kde" ;;
    *xfce*)     DE="xfce" ;;
    *cinnamon*) DE="cinnamon" ;;
    *mate*)     DE="mate" ;;
  esac
  if [[ "$DE" == "other" ]]; then
    if [[ -n "${GNOME_DESKTOP_SESSION_ID:-}" ]] || command -v gnome-shell >/dev/null 2>&1; then
      DE="gnome"
    elif command -v plasmashell >/dev/null 2>&1; then
      DE="kde"
    elif command -v xfce4-session >/dev/null 2>&1; then
      DE="xfce"
    fi
  fi
}

# ============================================================== entorno y sudo
check_env() {
  if (( EUID == 0 )); then IS_ROOT=true; else IS_ROOT=false; fi
  if command -v sudo >/dev/null 2>&1; then HAVE_SUDO=true; else HAVE_SUDO=false; fi
  if command -v flatpak >/dev/null 2>&1; then HAVE_FLATPAK=true; else HAVE_FLATPAK=false; fi
  INTERACTIVE=true
  if [[ -t 0 && -t 1 ]]; then INTERACTIVE=true; else INTERACTIVE=false; fi
}

# Ejecuta un comando como superusuario (directo si ya somos root)
run_sudo() {
  if [[ "$IS_ROOT" == true ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

# Ejecuta un array de comandos del gestor de paquetes (PM_*) respetando root
run_pm() {
  local -n _arr="$1"; shift
  local -a cmd
  if [[ "$IS_ROOT" == true ]]; then
    cmd=("${_arr[@]:1}")
  else
    cmd=("${_arr[@]}")
  fi
  if [[ ${#cmd[@]} -eq 0 ]]; then
    ui_alert "Comando de paquete vacío."
    return 1
  fi
  "${cmd[@]}" "$@"
}

# Verifica/cachea credenciales sudo; muestra aviso en la interfaz si falla
ensure_sudo() {
  if [[ "$IS_ROOT" == true ]]; then
    return 0
  fi
  if [[ "$HAVE_SUDO" == true ]]; then
    if sudo -v 2>/dev/null; then
      return 0
    fi
  fi
  if [[ "$IS_ROOT" == false && "$HAVE_SUDO" == false ]]; then
    ui_alert "Se requieren permisos de superusuario para esta operación.\nEjecuta Talarium con un usuario con acceso a sudo o como root."
  elif [[ "$HAVE_SUDO" == false ]]; then
    ui_alert "sudo no está disponible en este sistema.\nAlgunas operaciones pueden fallar sin privilegios de root."
  else
    ui_alert "La sesión de sudo ha expirado o falló.\nPor favor, vuelva a ingresar su contraseña."
  fi
  return 1
}

# ============================================================ consultas
# Comprueba si un paquete está instalado (acepta prefijos aur: y flatpak:)
is_installed() {
  local p="${1#aur:}"
  case "$p" in
    flatpak:*)
      is_flatpak_installed "${p#flatpak:}"
      return $?
      ;;
  esac
  case "$PM" in
    dnf|zypper) rpm -q "$p" >/dev/null 2>&1 ;;
    pacman)     pacman -Q "$p" >/dev/null 2>&1 ;;
    apt)        dpkg -s "$p" >/dev/null 2>&1 ;;
    xbps)       xbps-query "$p" >/dev/null 2>&1 ;;
    apk)        apk info -e "$p" >/dev/null 2>&1 ;;
    *)          return 1 ;;
  esac
}

is_flatpak_installed() {
  [[ "$HAVE_FLATPAK" == true ]] && flatpak info "$1" >/dev/null 2>&1
}

# Instala los paquetes dados omitiendo los ya instalados (rápido y seguro).
# Admite prefijo aur: cuando el gestor es pacman y existe helper AUR,
# y prefijo flatpak: para aplicaciones instaladas desde Flathub.
pm_install() {
  local -a pend=() norm=() aur=() flat=()
  local p
  for p in "$@"; do
    is_installed "$p" || pend+=("$p")
  done
  ((${#pend[@]} == 0)) && { echo "  Todos los paquetes ya estaban instalados."; return 0; }

  for p in "${pend[@]}"; do
    case "$p" in
      aur:*)     aur+=("${p#aur:}") ;;
      flatpak:*) flat+=("${p#flatpak:}") ;;
      *)         norm+=("$p") ;;
    esac
  done

  if ((${#norm[@]} > 0)); then
    echo ">> Instalando: ${norm[*]}"
    if ! run_pm PM_INSTALL "${norm[@]}"; then
      # apt y zypper fallan la transacción completa si falta un paquete:
      # reintento individual para no perder el resto del lote.
      if [[ "$PM" == "apt" || "$PM" == "zypper" ]]; then
        echo "  Reintento individual (alguno no estaba disponible)..."
        for p in "${norm[@]}"; do
          run_pm PM_INSTALL "$p" >/dev/null 2>&1 || echo "  No disponible: $p"
        done
      else
        return 1
      fi
    fi
  fi

  if ((${#aur[@]} > 0)); then
    if [[ -z "$AUR_HELPER" ]]; then
      echo "  AUR: no se encontró paru/yay para: ${aur[*]} (instálalo en Recomendaciones)."
      return 1
    fi
    echo ">> Instalando desde AUR: ${aur[*]}"
    run_sudo "$AUR_HELPER" -S --noconfirm --needed "${aur[@]}"
  fi

  if ((${#flat[@]} > 0)); then
    if ! command -v flatpak >/dev/null 2>&1; then
      echo "  flatpak no está instalado. Instálalo antes (categoría 'esenciales')."
      return 1
    fi
    if ! flatpak remotes 2>/dev/null | grep -qi flathub; then
      echo ">> Añadiendo repositorio Flathub..."
      run_sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
    fi
    echo ">> Instalando (Flatpak): ${flat[*]}"
    run_sudo flatpak install -y flathub "${flat[@]}"
  fi
  return 0
}

# Elimina los paquetes dados que sí estén instalados
# (acepta también prefijo flatpak: para apps instaladas desde Flathub)
pm_remove() {
  local -a pend=() flat=()
  local p
  for p in "$@"; do
    case "$p" in
      flatpak:*)
        [[ "$HAVE_FLATPAK" == true ]] && flat+=("${p#flatpak:}")
        ;;
      *) is_installed "$p" && pend+=("$p") ;;
    esac
  done

  if ((${#flat[@]} > 0)); then
    echo ">> Eliminando (Flatpak): ${flat[*]}"
    run_sudo flatpak uninstall -y "${flat[@]}"
  fi

  ((${#pend[@]} == 0)) && { echo "  Nada que eliminar (nativo)."; return 0; }
  echo ">> Eliminando: ${pend[*]}"
  run_pm PM_REMOVE "${pend[@]}"
}

# ============================================================ info del sistema
sys_mem_gb() { free -g 2>/dev/null | awk '/^Mem:/{print $2+0}'; }
sys_cores()  { nproc 2>/dev/null; }

# true si no hay ningún disco giratorio (HDD)
sys_is_ssd() {
  command -v lsblk >/dev/null 2>&1 || return 1
  local rot
  rot=$(lsblk -dn -o ROTA 2>/dev/null | grep -c '1')
  [[ "${rot:-0}" == "0" ]] && return 0 || return 1
}

# nvidia | amd | intel | desconocida
sys_gpu_vendor() {
  local v=""
  if command -v lspci >/dev/null 2>&1; then
    v=$(lspci -nn 2>/dev/null | grep -iE 'vga|3d controller' | head -1)
  fi
  case "$v" in
    *[Nn][Vv][Ii][Dd][Ii][Aa]*) echo "nvidia" ;;
    *[Aa][Mm][Dd]*)             echo "amd" ;;
    *[Ii][Nn][Tt][Ee][Ll]*)     echo "intel" ;;
    *)
      local dev
      for dev in /sys/class/drm/card*/device/vendor; do
        [[ -r "$dev" ]] || continue
        case "$(cat "$dev" 2>/dev/null)" in
          0x10de) echo "nvidia"; return ;;
          0x1002) echo "amd"; return ;;
          0x8086) echo "intel"; return ;;
        esac
      done
      echo "desconocida" ;;
  esac
}

# ================================================================ auxiliares
detect_aur_helper() {
  AUR_HELPER=""
  if [[ "$PM" == "pacman" ]]; then
    command -v paru >/dev/null 2>&1 && AUR_HELPER="paru"
    command -v yay  >/dev/null 2>&1 && AUR_HELPER="yay"
  fi
}

is_systemd() {
  command -v systemctl >/dev/null 2>&1 && [[ -d /run/systemd/system ]]
}
