#!/usr/bin/env bash
# =============================================================================
#  Talarium - Gestor de sistema para Linux (creado por sebvillacorta / RevOst)
#  Soporta: Fedora/RHEL (dnf), Arch (pacman+AUR), Debian/Ubuntu (apt),
#           openSUSE (zypper), Void (xbps)
#  Uso: ./talarium.sh [--doctor|--help]
# =============================================================================

set -o pipefail
shopt -s extglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TALARIUM_ROOT="$SCRIPT_DIR"
export TALARIUM_LIB="$SCRIPT_DIR/lib"
export TALARIUM_CONFIG="$SCRIPT_DIR/config"

for mod in core ui packages debloat tweaks recommend backup; do
  # shellcheck disable=SC1090
  source "$TALARIUM_LIB/$mod.sh" || { echo "Error: no se pudo cargar lib/$mod.sh"; exit 1; }
done

TALARIUM_VERSION="1.0.0"
BACKTITLE="Talarium v$TALARIUM_VERSION · RevOst | Gestor de sistema para Linux"

# =============================================================================
main() {
  case "${1:-}" in
    --doctor) doctor; return 0 ;;
    --help|-h|help) usage; return 0 ;;
    "") ;;
    *) usage; return 1 ;;
  esac

  bootstrap || return 1
  loop_menu
}

# =============================================================================
bootstrap() {
  detect_distro
  detect_de
  detect_ui
  check_env

  if [[ -z "$PM" ]]; then
    ui_alert "Tu distribución (${DISTRO_NAME}) no está soportada todavía.\nGestores soportados: dnf, pacman, apt, zypper, xbps."
    return 1
  fi

  show_welcome
  maybe_upgrade_ui
  return 0
}

# =============================================================================
# Si solo hay whiptail, ofrece instalar dialog (interfaz más completa)
maybe_upgrade_ui() {
  if [[ "$UI_ENGINE" == "whiptail" ]]; then
    set_backtitle ""
    if ui_yesno "Interfaz" "Instalar 'dialog' para una interfaz más completa y bonita?"; then
      ensure_sudo && run_pm PM_INSTALL dialog
      detect_ui
    fi
  fi
}

# =============================================================================
loop_menu() {
  while true; do
    local sel
    set_backtitle ""
    sel=$(ui_menu "Talarium - Panel principal" \
      "Sistema: ${DISTRO_NAME} ${DISTRO_VERSION} | Escritorio: ${DE^} | Gestor: ${PM}" \
      "soft"   "Software: instalar / desinstalar aplicaciones" \
      "sys"    "Sistema: limpieza, desbloat y mantenimiento" \
      "visual" "Visual: ajustes gráficos e interfaz" \
      "tips"   "Consejos: recomendaciones según tu equipo" \
      "backup" "Copia de seguridad y restauración" \
      "help"   "Ayuda e información" \
      "exit"   "Salir") || break

    case "$sel" in
      soft)   menu_software ;;
      sys)    menu_sistema ;;
      visual) menu_visual ;;
      tips)   menu_recomendaciones ;;
      backup) menu_backup ;;
      help)   menu_ayuda ;;
      exit|"") break ;;
    esac
  done
  farewell
}

# =============================================================================
menu_ayuda() {
  set_backtitle help
  ui_alert "Talarium v${TALARIUM_VERSION} - Gestor de sistema para Linux

Panel de pestañas:
  1. Software  -> instalar/desinstalar por categorías
  2. Sistema   -> desbloat, huérfanos, cachés, journal, actualizar
  3. Visual    -> ajustes gráficos (GNOME/KDE/XFCE), fuentes, zsh, TRIM
  4. Consejos  -> recomendaciones según tu hardware y distro
  5. Backup    -> copia de seguridad y restauración

Seguridad: nada se instala ni elimina sin tu confirmación.
Nada se ejecuta como root de forma implícita: Talarium pide sudo cuando lo necesita.

Más opciones:
  ./talarium.sh --doctor   Diagnóstico del sistema
  ./talarium.sh --help     Ayuda"
}

# =============================================================================
doctor() {
  detect_distro
  detect_de
  detect_ui
  check_env
  echo "==================  Talarium - Diagnóstico  =================="
  echo "  Distro          : ${DISTRO_NAME} (${DISTRO_ID}) ${DISTRO_VERSION}"
  echo "  Gestor de paq.  : ${PM:-NO SOPORTADO}"
  echo "  Escritorio      : ${DE^}"
  echo "  Interfaz        : ${UI_ENGINE}${UI:+ ($UI)}"
  echo "  AUR helper      : ${AUR_HELPER:-ninguno}"
  echo "  Flatpak         : $(command -v flatpak >/dev/null 2>&1 && echo disponible || echo no)"
  echo "  Root            : ${IS_ROOT} | Sudo: ${HAVE_SUDO}"
  echo "  RAM             : $(sys_mem_gb) GB | CPU: $(sys_cores) núcleos | GPU: $(sys_gpu_vendor)"
  echo "  Disco           : $(sys_is_ssd && echo SSD || echo HDD)"
  echo "  Backups         : $BACKUP_BASE"
  echo "  Config software : $(ls "$TALARIUM_CONFIG/software/" 2>/dev/null | tr '\n' ' ')"
  echo "  Config debloat  : $(ls "$TALARIUM_CONFIG/debloat/" 2>/dev/null | tr '\n' ' ')"
  echo "==========================================================="
}

# =============================================================================
usage() {
  echo "Uso: ./talarium.sh [opcion]"
  echo
  echo "  (sin opciones)   Abre el menú interactivo"
  echo "  --doctor         Muestra el diagnóstico del sistema y sale"
  echo "  --help           Muestra esta ayuda"
  echo
  echo "Requisitos: bash 4.3+, sudo y opcionalmente dialog/whiptail."
}

# =============================================================================
main "$@"
