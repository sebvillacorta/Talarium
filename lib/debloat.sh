#!/usr/bin/env bash
# =============================================================================
# debloat.sh - Limpieza y desbloat del sistema
# Las listas de bloat viven en config/debloat/<escritorio>.conf y
# config/debloat/<distro>.conf
# =============================================================================

# ---------------------------------------------------------- menú principal
menu_sistema() {
  local sel
  set_backtitle sys
  sel=$(ui_menu "Sistema - limpieza y mantenimiento" \
    "bloat"   "Eliminar software preinstalado (bloat)" \
    "huerf"   "Limpiar paquetes huérfanos o sin uso" \
    "cache"   "Limpiar cachés del sistema" \
    "journal" "Compactar registros del sistema (journal)" \
    "update"  "Actualizar el sistema completo" \
    "back"    "Volver al menú principal")
  case "$sel" in
    bloat)   debloat_pick ;;
    huerf)   debloat_orphans ;;
    cache)   debloat_cache ;;
    journal) debloat_journal ;;
    update)  run_update_system ;;
    *)       return ;;
  esac
}

# -------------------------------------------------- eliminar bloat por DE/distro
debloat_pick() {
  local -a items=()
  local confs=("$TALARIUM_CONFIG/debloat/$DE.conf" "$TALARIUM_CONFIG/debloat/$DISTRO_ID.conf")
  local conf p

  for conf in "${confs[@]}"; do
    [[ -r "$conf" ]] || continue
    while read -r p; do
      [[ -n "$p" && "$p" != '#'* ]] || continue
      if is_installed "$p"; then
        items+=("$p" "[INSTALADO] $p" "off")
      fi
    done < "$conf"
  done

  if ((${#items[@]} == 0)); then
    ui_alert "No se detectó software desinstalable para ${DE^} / ${DISTRO_NAME}."
    return
  fi

  local chosen
  chosen=$(ui_checklist "Desbloat - ${DE^}" \
    "Marca con ESPACIO lo que quieras ELIMINAR" \
    "${items[@]}") || return
  [[ -n "$chosen" ]] || { ui_alert "No seleccionaste nada."; return; }

  ui_yesno "Confirmar eliminación" "Se eliminarán del sistema:\n${chosen}" || return
  ensure_sudo || return 1
  ui_info "Eliminando bloat"
  pm_remove $chosen
  ui_pause
}

# -------------------------------------------------- paquetes huérfanos
debloat_orphans() {
  ensure_sudo || return 1
  ui_info "Limpiando paquetes huérfanos"
  local found=0
  case "$PM" in
    dnf)
      run_sudo dnf autoremove -y && found=1
      ;;
    pacman)
      local orphan
      orphan=$(pacman -Qdtq 2>/dev/null)
      if [[ -n "$orphan" ]]; then
        echo ">> Eliminando huérfanos: $(echo "$orphan" | tr '\n' ' ')"
        # shellcheck disable=SC2086  # lista de paquetes separados por espacios
        run_sudo pacman -Rns --noconfirm $orphan
        found=1
      else
        echo "  No hay paquetes huérfanos."
      fi
      ;;
    apt)
      run_sudo apt-get autoremove -y --purge && found=1
      ;;
    zypper)
      run_sudo zypper remove -y --clean-deps && found=1
      ;;
    *)
      ui_alert "Operación no soportada para el gestor '$PM'."
      ;;
  esac
  if [[ "$found" -eq 1 ]]; then
    ui_pause
  fi
}

# -------------------------------------------------- cachés
debloat_cache() {
  ensure_sudo || return 1
  ui_info "Limpiando cachés"
  case "$PM" in
    dnf)    run_sudo dnf clean all ;;
    pacman) run_sudo pacman -Scc --noconfirm ;;
    apt)    run_sudo apt-get clean ;;
    zypper) run_sudo zypper clean -a ;;
    *)      ui_alert "Gestor '$PM' sin limpieza definida." ;;
  esac

  if [[ "$HAVE_FLATPAK" == true ]]; then
    echo ">> Flatpak sin uso..."
    run_sudo flatpak uninstall --unused -y 2>/dev/null || echo "  (sin flatpak sin uso para eliminar)"
  fi

  echo ">> Cachés de usuario (~/.cache)..."
  if [[ -d "$HOME/.cache" ]]; then
    local cache_size
    cache_size=$(du -sh "$HOME/.cache" 2>/dev/null | cut -f1)
    find "$HOME/.cache" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null
    local new_size="0"
    [[ -d "$HOME/.cache" ]] && new_size=$(du -sh "$HOME/.cache" 2>/dev/null | cut -f1 || echo "0")
    echo "  Cachés liberados: ${cache_size:-0} -> ${new_size:-0}"
  else
    echo "  No hay caché de usuario para limpiar."
  fi
  echo "  Cachés limpiadas."
  ui_pause
}

# -------------------------------------------------- journal
debloat_journal() {
  if ! is_systemd; then
    ui_alert "Este sistema no usa systemd/journal."
    return
  fi
  ensure_sudo || return 1
  ui_info "Compactando journal (se conservan 10 días)"
  if run_sudo journalctl --vacuum-time=10d; then
    ui_step "Journal compactado exitosamente."
  else
    ui_alert "No se pudo compactar el journal. Verifique permisos."
  fi
  ui_pause
}

# -------------------------------------------------- actualización completa
run_update_system() {
  ensure_sudo || return 1
  ui_info "Actualizando el sistema"
  case "$PM" in
    dnf)
      run_sudo dnf upgrade -y || ui_alert "Error durante la actualización con dnf."
      ;;
    pacman)
      run_sudo pacman -Syu --noconfirm || ui_alert "Error durante la actualización con pacman."
      ;;
    apt)
      run_sudo apt-get update || ui_alert "Error al actualizar la lista de paquetes."
      run_sudo apt-get upgrade -y || ui_alert "Error durante la actualización con apt."
      ;;
    zypper)
      run_sudo zypper update -y || ui_alert "Error durante la actualización con zypper."
      ;;
    *)
      ui_alert "Gestor '$PM' no soportado."
      return 1
      ;;
  esac

  if [[ "$HAVE_FLATPAK" == true ]]; then
    echo ">> Actualizando aplicaciones Flatpak..."
    run_sudo flatpak update -y 2>/dev/null || echo "  (error actualizando flatpak)"
  fi
  echo "  Sistema actualizado."
  ui_pause
}
