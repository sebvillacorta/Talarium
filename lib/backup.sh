#!/usr/bin/env bash
# =============================================================================
# backup.sh - Copia de seguridad y restauración (paquetes + configuración)
# =============================================================================

BACKUP_BASE="$HOME/Talarium-backups"

# ---------------------------------------------------------- menú principal
menu_backup() {
  local sel
  set_backtitle backup
  sel=$(ui_menu "Copia de seguridad" \
    "create"  "Crear copia (paquetes instalados + configuración)" \
    "restore" "Restaurar desde la copia más reciente" \
    "list"    "Ver copias existentes" \
    "back"    "Volver al menú principal")
  case "$sel" in
    create)  backup_create ;;
    restore) backup_restore ;;
    list)    backup_list ;;
    *)       return ;;
  esac
}

# ---------------------------------------------------------- crear
backup_create() {
  mkdir -p "$BACKUP_BASE"
  local stamp dir
  stamp=$(date +%Y%m%d-%H%M%S)
  dir="$BACKUP_BASE/$stamp"
  mkdir -p "$dir"

  ui_info "Creando copia de seguridad"
  echo ">> $dir"

  case "$PM" in
    dnf)
      if dnf repoquery --userinstalled >"$dir/paquetes.txt" 2>/dev/null; then :; else
        rpm -qa --qf '%{NAME}\n' | sort >"$dir/paquetes.txt"
      fi
      ;;
    pacman)
      pacman -Qeq >"$dir/paquetes.txt" 2>/dev/null
      ;;
    apt)
      apt-mark showmanual >"$dir/paquetes.txt" 2>/dev/null
      ;;
    zypper)
      zypper se --installed-only 2>/dev/null | awk 'NR>1{print $3}' | sort -u >"$dir/paquetes.txt"
      [[ -s "$dir/paquetes.txt" ]] || rpm -qa --qf '%{NAME}\n' | sort >"$dir/paquetes.txt"
      ;;
    *)
      echo "  Gestor '$PM' sin exportador definido."
      ;;
  esac

  if [[ -s "$dir/paquetes.txt" ]]; then
    echo "  $(wc -l < "$dir/paquetes.txt") paquetes exportados."
  fi

  if command -v dconf >/dev/null 2>&1; then
    dconf dump / >"$dir/dconf.dump" 2>/dev/null && echo "  Configuración del escritorio exportada."
  fi

  echo
  echo "  Copias existentes:"
  ls -1t "$BACKUP_BASE" 2>/dev/null | head -5 | sed 's/^/    - /'
  ui_pause
}

# ---------------------------------------------------------- listar
backup_list() {
  local n
  n=$(ls -1 "$BACKUP_BASE" 2>/dev/null | wc -l)
  if (( n == 0 )); then
    ui_alert "No hay copias de seguridad todavía."
    return
  fi
  ui_alert "Copias existentes:\n\n$(ls -1t "$BACKUP_BASE" 2>/dev/null | head -10 | sed 's/^/• /')"
}

# ---------------------------------------------------------- restaurar
backup_restore() {
  local latest
  latest=$(ls -1t "$BACKUP_BASE" 2>/dev/null | head -1)
  if [[ -z "$latest" ]]; then
    ui_alert "No hay copias de seguridad."
    return
  fi
  ui_yesno "Restaurar" "Se restaurará la copia:\n$latest\n\nEsto reinstalará los paquetes que falten." || return
  ensure_sudo || return 1

  ui_info "Restaurando paquetes (se omiten los ya instalados)"
  local pkg n=0
  while read -r pkg; do
    [[ -n "$pkg" ]] || continue
    is_installed "$pkg" && continue
    case "$PM" in
      dnf)    run_sudo dnf install -y "$pkg" >/dev/null 2>&1 ;;
      pacman) run_sudo pacman -S --noconfirm --needed "$pkg" >/dev/null 2>&1 ;;
      apt)    run_sudo apt-get install -y "$pkg" >/dev/null 2>&1 ;;
      zypper) run_sudo zypper install -y "$pkg" >/dev/null 2>&1 ;;
    esac
    ((n++))
  done < "$BACKUP_BASE/$latest/paquetes.txt"
  echo "  Paquetes reinstalados: $n"

  if [[ -f "$BACKUP_BASE/$latest/dconf.dump" ]] && command -v dconf >/dev/null 2>&1; then
    if ui_yesno "Configuración" "¿Restaurar también la configuración del escritorio?"; then
      dconf load / <"$BACKUP_BASE/$latest/dconf.dump"
      echo "  Configuración restaurada."
    fi
  fi
  ui_pause
}
