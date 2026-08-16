#!/usr/bin/env bash
# =============================================================================
# tweaks.sh - Ajustes gráficos y de interfaz (GNOME / KDE / XFCE)
# =============================================================================

# ---------------------------------------------------------- menú principal
menu_visual() {
  local sel
  set_backtitle visual
  sel=$(ui_menu "Visual - apariencia y rendimiento" \
    "de"    "Ajustes del escritorio actual (${DE^})" \
    "fonts" "Instalar fuentes de programación (JetBrains Mono, Fira Code)" \
    "zsh"   "Instalar Zsh + Oh My Zsh (mejor terminal)" \
    "ssd"   "Activar TRIM automático para SSD (fstrim)" \
    "back"  "Volver al menú principal")
  case "$sel" in
    de)    tweaks_de ;;
    fonts) tweaks_fonts ;;
    zsh)   tweaks_zsh ;;
    ssd)   tweaks_ssd ;;
    *)     return ;;
  esac
}

# ---------------------------------------------------------- por escritorio
tweaks_de() {
  case "$DE" in
    gnome) tweaks_gnome ;;
    kde)   tweaks_kde ;;
    xfce)  tweaks_xfce ;;
    *)
      ui_alert "El escritorio ${DE^} aún no tiene ajustes específicos definidos."
      ;;
  esac
}

# ================================================================ GNOME
tweaks_gnome() {
  if ! command -v gsettings >/dev/null 2>&1; then
    ui_alert "gsettings no está disponible en este sistema."
    return
  fi
  local sel
  sel=$(ui_menu "Ajustes GNOME" \
    "dark"  "Modo oscuro (tema y aplicaciones)" \
    "btns"  "Mostrar botones minimizar/maximizar en ventanas" \
    "tap"   "Activar 'tocar para hacer clic' en el touchpad" \
    "night" "Activar luz nocturna (pantalla cálida al anochecer)" \
    "anim"  "Desactivar animaciones (respuesta más rápida)" \
    "week"  "Mostrar números de semana en el calendario" \
    "back"  "Volver")
  case "$sel" in
    dark)
      gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
      gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita-dark'
      ui_step "Modo oscuro activado."
      ;;
    btns)
      gsettings set org.gnome.desktop.wm.preferences button-layout 'appmenu:minimize,maximize,close'
      ui_step "Botones de ventana configurados."
      ;;
    tap)
      gsettings set org.gnome.desktop.peripherals.touchpad tap-to-click true
      ui_step "Tap-to-click activado."
      ;;
    night)
      gsettings set org.gnome.settings-daemon.plugins.color night-light-enabled true
      gsettings set org.gnome.settings-daemon.plugins.color night-light-schedule-automatic true
      ui_step "Luz nocturna activada."
      ;;
    anim)
      gsettings set org.gnome.desktop.interface enable-animations false
      ui_step "Animaciones desactivadas."
      ;;
    week)
      gsettings set org.gnome.desktop.calendar show-weekdate true
      ui_step "Semanas visibles en el calendario."
      ;;
  esac
  ui_pause
}

# ================================================================ KDE
tweaks_kde() {
  local sel
  sel=$(ui_menu "Ajustes KDE Plasma" \
    "dark" "Tema oscuro BreezeDark" \
    "back" "Volver")
  case "$sel" in
    dark)
      if command -v plasma-apply-colorscheme >/dev/null 2>&1; then
        plasma-apply-colorscheme BreezeDark >/dev/null 2>&1
        ui_step "Tema BreezeDark aplicado."
      else
        local kc=""
        command -v kwriteconfig6 >/dev/null 2>&1 && kc="kwriteconfig6"
        command -v kwriteconfig5 >/dev/null 2>&1 && kc="kwriteconfig5"
        if [[ -n "$kc" ]]; then
          "$kc" --file kdeglobals --group General --key ColorScheme BreezeDark
          ui_step "Color configurado. Reinicia sesión para ver el cambio."
        else
          ui_alert "No se encontró kwriteconfig ni plasma-apply-colorscheme."
        fi
      fi
      ;;
  esac
  ui_pause
}

# ================================================================ XFCE
tweaks_xfce() {
  if command -v xfconf-query >/dev/null 2>&1; then
    xfconf-query -c xsettings -p /Net/ThemeName -s "Adwaita-dark" 2>/dev/null
    ui_step "Tema Adwaita-dark aplicado."
  else
    ui_alert "xfconf no está disponible."
  fi
  ui_pause
}

# ================================================================ fuentes
tweaks_fonts() {
  ensure_sudo || return 1
  ui_info "Instalando fuentes de programación"
  case "$PM" in
    dnf)    run_pm PM_INSTALL jetbrains-mono-fonts fira-code-fonts ;;
    pacman) run_pm PM_INSTALL ttf-jetbrains-mono ttf-fira-code ;;
    apt)    run_pm PM_INSTALL fonts-jetbrains-mono fonts-firacode ;;
    zypper) run_pm PM_INSTALL jetbrains-mono-fonts fira-code-fonts ;;
    *)      ui_alert "Fuentes no definidas para el gestor '$PM'."; return ;;
  esac
  ui_step "JetBrains Mono y Fira Code instaladas."
  ui_pause
}

# ================================================================ zsh
tweaks_zsh() {
  ensure_sudo || return 1
  ui_info "Preparando Zsh + Oh My Zsh"
  if ! command -v zsh >/dev/null 2>&1; then
    case "$PM" in
      dnf|pacman|apt|zypper) run_pm PM_INSTALL zsh ;;
      *) ui_alert "Instalación de zsh no definida para '$PM'."; return ;;
    esac
  fi

  if [[ ! -d "$HOME/.oh-my-zsh" ]]; then
    if command -v git >/dev/null 2>&1; then
      echo ">> Descargando Oh My Zsh..."
      if command -v curl >/dev/null 2>&1; then
        RUNZSH=no CHSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended >/dev/null 2>&1
      fi
      [[ -d "$HOME/.oh-my-zsh" ]] || git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git "$HOME/.oh-my-zsh" >/dev/null 2>&1
      [[ -f "$HOME/.zshrc" ]] || cp "$HOME/.oh-my-zsh/templates/zshrc.zsh-template" "$HOME/.zshrc"
      ui_step "Oh My Zsh instalado."
    else
      ui_alert "Se necesita 'git' para instalar Oh My Zsh."
    fi
  fi

  if command -v zsh >/dev/null 2>&1 && [[ "$SHELL" != *zsh ]]; then
    if ui_yesno "Shell por defecto" "¿Usar zsh como shell predeterminada?"; then
      chsh -s "$(command -v zsh)"
      ui_step "Shell cambiada (se aplica al reabrir la terminal)."
    fi
  fi
  ui_pause
}

# ================================================================ SSD TRIM
tweaks_ssd() {
  if ! sys_is_ssd; then
    ui_alert "No se detectó un disco SSD. TRIM no es necesario."
    return
  fi
  if ! is_systemd; then
    ui_alert "Este sistema no usa systemd (fstrim.timer no aplica)."
    return
  fi
  ensure_sudo || return 1
  if ! systemctl enable --now fstrim.timer 2>/dev/null; then
    ui_alert "No se pudo activar fstrim.timer. Verifique que el servicio esté disponible."
    return
  fi
  ui_step "TRIM automático activado (fstrim.timer)."
  ui_pause
}
