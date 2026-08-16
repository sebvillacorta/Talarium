#!/usr/bin/env bash
# =============================================================================
# ui.sh - Motor de interfaz TUI para Talarium (tema monocromo)
# Prioridad: dialog  ->  whiptail  ->  menú de texto plano
# =============================================================================

# --------------------------------------------------------------- colores ANSI
# Tema monocromo: todo se muestra en blanco sobre negro
# shellcheck disable=SC2034  # API de color monocromo (C_RED..C_MAGENTA = blanco)
C_RESET=$'\e[0m'; C_BOLD=$'\e[1m'; C_DIM=$'\e[2m'
C_WHITE=$'\e[37m'
C_RED=$C_WHITE; C_GREEN=$C_WHITE; C_YELLOW=$C_WHITE
C_CYAN=$C_WHITE; C_MAGENTA=$C_WHITE

# shellcheck disable=SC2034  # UI/UI_ENGINE consultados como variables globales
UI_ENGINE="texto"          # dialog | whiptail | texto
UI=""
_WHIPTAIL_STDOUT=false

# Descripciones para el selector con cursor (tag -> texto).
# Lo rellena packages.sh antes de llamar a ui_checklist_sel.
declare -A NAV_DESC=()

# ============================================================ detección UI
detect_ui() {
  UI_ENGINE="texto"; UI=""
  if command -v dialog >/dev/null 2>&1; then
    UI_ENGINE="dialog"; UI="dialog"
  elif command -v whiptail >/dev/null 2>&1; then
    UI_ENGINE="whiptail"; UI="whiptail"
    if whiptail --help 2>&1 | grep -q -- '--stdout'; then
      _WHIPTAIL_STDOUT=true
    fi
  fi
  apply_mono_theme
}

# ============================================================ tema monocromo
# whiptail (newt): paleta blanco/negro vía NEWT_COLORS
# dialog:          paleta vía archivo DIALOGRC (config/theme/dialog.mono)
apply_mono_theme() {
  case "$UI_ENGINE" in
    whiptail)
      export NEWT_COLORS="root=white,black;border=white,black;shadow=black,gray;title=white,black;button=white,black;actbutton=black,white;checkbox=white,black;actcheckbox=black,white;entry=white,black;actentry=black,white;label=white,black;listbox=white,black;actlistbox=black,white;textbox=white,black;acttextbox=black,white;helpline=white,black;sellistbox=white,black;actsellistbox=black,white;emptyscale=white,black;fullscale=black,white;compactbutton=black,white"
      ;;
    dialog)
      export DIALOGRC="$TALARIUM_CONFIG/theme/dialog.mono"
      ;;
  esac
}

# ============================================================ barra pestañas
# Construye el BACKTITLE estilo pestañas: la activa va entre corchetes
# Uso: set_backtitle soft|sys|visual|tips|backup|help|""
set_backtitle() {
  local active="${1:-}"
  local -a tags=(soft sys visual tips backup help exit)
  local -a names=(Software Sistema Visual Consejos Backup Ayuda Salir)
  local i bar=""
  for ((i=0; i<${#tags[@]}; i++)); do
    if [[ "${tags[i]}" == "$active" ]]; then
      bar+=" [${names[i]}]"
    else
      bar+=" ${names[i]} "
    fi
  done
  BACKTITLE="Talarium v$TALARIUM_VERSION · RevOst |$bar"
}

# ============================================================ pantalla inicio
# Splash de bienvenida: banner ASCII + descripción, centrado según ancho de
# la terminal. 100% texto plano (sin dialog) para que el arte permanezca
# visible: dialog usa pantalla alternativa y ocultaría el banner.
# Enter/S = Continuar · N/C/Esc = Cancelar
show_welcome() {
  clear
  local cols pad padbtn padmsg line
  cols=$(tput cols 2>/dev/null || echo 80)
  while IFS= read -r line; do
    if [[ -z "$line" ]]; then
      echo
    else
      pad=$(( (cols - ${#line}) / 2 ))
      (( pad < 0 )) && pad=0
      printf '%*s%s\n' "$pad" "" "$line"
    fi
  done <<'EOF'
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║       ████████╗ █████╗ ██╗      █████╗ ██████╗ ██╗██╗   ██╗███╗   ███╗       ║
║       ╚══██╔══╝██╔══██╗██║     ██╔══██╗██╔══██╗██║██╗   ██║████╗ ████║       ║
║          ██║   ███████║██║     ███████║██████╔╝██║██║   ██║██╔████╔██║       ║
║          ██║   ██╔══██║██║     ██╔══██║██╔══██╗██║██║   ██║██║╚██╔╝██║       ║
║          ██║   ██║  ██║███████╗██║  ██║██║  ██║██║╚██████╔╝██║ ╚═╝ ██║       ║
║          ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝     ╚═╝       ║
║                                                                              ║
║       Gestor de sistema para Linux  ·  v1.0.0  ·  100% TUI (terminal)        ║
║            Motor: dialog - whiptail - texto   ·   Tema: monocromo            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════╗
║  Talarium: gestor de sistema para Linux. Creado por sebvillacorta            ║
║  (alias RevOst). Instala software por categorias, limpia paquetes            ║
║  innecesarios, ajusta la interfaz grafica, recomienda optimizaciones         ║
║  segun tu equipo y respaldas tu configuracion. Todo desde la terminal,        ║
║  100% TUI. Nada se instala sin tu confirmacion.                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

EOF

  padbtn=$(( (cols - 40) / 2 )); (( padbtn < 0 )) && padbtn=0
  printf '%*s%s\n' "$padbtn" "" "${C_WHITE}${C_BOLD}┌─────────────────┐${C_RESET}   ${C_DIM}┌──────────────┐${C_RESET}"
  printf '%*s%s\n' "$padbtn" "" "${C_WHITE}${C_BOLD}│  » Continuar «  │${C_RESET}   ${C_DIM}│  Cancelar    │${C_RESET}"
  printf '%*s%s\n' "$padbtn" "" "${C_WHITE}${C_BOLD}└─────────────────┘${C_RESET}   ${C_DIM}└──────────────┘${C_RESET}"
  padmsg=$(( (cols - 38) / 2 )); (( padmsg < 0 )) && padmsg=0
  printf '%*s%s\n\n' "$padmsg" "" "${C_DIM}Enter o S = continuar   ·   N o Esc = cancelar${C_RESET}"
  while true; do
    printf '%*s%s' "$(( (cols + 2) / 2 ))" "" "→ "
    read -rsn1 k || { farewell; exit 0; }
    case "${k,,}" in
      ""|s|y) clear; return 0 ;;
      n|c|$'\e') farewell; exit 0 ;;
    esac
  done
}

# ============================================================ despedida
# Marca del creador en arte ASCII (misma fuente de bloques que el logo)
print_revost() {
  while IFS= read -r line; do
    local pad
    pad=$(( (COLS - ${#line}) / 2 )); (( pad < 0 )) && pad=0
    printf '%*s%s\n' "$pad" "" "$line"
  done <<'EOF'
  ██████╗    ███████╗   ██╗   ██╗  ██████╗    ███████╗   ████████╗
  ██╔══██╗   ██╔════╝   ██║   ██║  ██╔══██╗   ██╔════╝   ╚══██╔══╝
  ██████╔╝   █████╗     ██║   ██║  ██║  ██║   ███████╗      ██║   
  ██╔══██╗   ██╔══╝     ╚██╗ ██╔╝  ██║  ██║   ╚════██║      ██║   
  ██║  ██║   ███████╗    ╚████╔╝   ╚██████╔╝  ███████║      ██║   
  ╚═╝  ╚═╝   ╚══════╝     ╚═══╝     ╚═════╝   ╚══════╝      ╚═╝   
EOF
}

# Despedida final: gracias + marca del creador, todo centrado
farewell() {
  clear
  local cols pad
  cols=$(tput cols 2>/dev/null || echo 80)
  COLS="$cols"
  echo
  pad=$(( (cols - 39) / 2 )); (( pad < 0 )) && pad=0
  printf '%*s%s\n\n' "$pad" "" "${C_WHITE}${C_BOLD}Gracias por usar Talarium. Hasta pronto.${C_RESET}"
  print_revost
  echo
  pad=$(( (cols - 40) / 2 )); (( pad < 0 )) && pad=0
  printf '%*s%s\n\n' "$pad" "" "${C_DIM}sebvillacorta · alias RevOst · v${TALARIUM_VERSION}${C_RESET}"
}

# ============================================================ banner
print_banner() {
  clear
  echo -e "${C_WHITE}${C_BOLD}"
  echo "  ████████╗ █████╗ ██╗      █████╗ ██████╗ ██╗██╗   ██╗███╗   ███╗"
  echo "  ╚══██╔══╝██╔══██╗██║     ██╔══██╗██╔══██╗██║██║   ██║████╗ ████║"
  echo "     ██║   ███████║██║     ███████║██████╔╝██║██║   ██║██╔████╔██║"
  echo "     ██║   ██╔══██║██║     ██╔══██║██╔══██╗██║██║   ██║██║╚██╔╝██║"
  echo "     ██║   ██║  ██║███████╗██║  ██║██║  ██║██║╚██████╔╝██║ ╚═╝ ██║"
  echo "     ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝     ╚═╝"
  echo -e "${C_RESET}"
  echo -e "  ${C_WHITE}${C_BOLD}Gestor de sistema para Linux${C_RESET}   ${C_DIM}v${TALARIUM_VERSION}${C_RESET}"
  echo
}

# ============================================================ menú (pestañas)
ui_menu() {
  local title="$1" text="$2"; shift 2
  local out=""
  case "$UI_ENGINE" in
    dialog)
      local -a args=()
      while (($# >= 2)); do args+=("$1" "$2"); shift 2; done
      out=$(dialog --stdout --backtitle "$BACKTITLE" --title "$title" \
            --menu "$text" 0 0 0 "${args[@]}") || return 1
      ;;
    whiptail)
      local -a args=()
      while (($# >= 2)); do args+=("$1" "$2"); shift 2; done
      if [[ "$_WHIPTAIL_STDOUT" == true ]]; then
        out=$(whiptail --stdout --backtitle "$BACKTITLE" --title "$title" \
              --menu "$text" 0 0 0 "${args[@]}") || return 1
      else
        out=$(whiptail --backtitle "$BACKTITLE" --title "$title" \
              --menu "$text" 0 0 0 "${args[@]}" 3>&1 1>&2 2>&3) || return 1
      fi
      ;;
    texto)
      out=$(texto_menu "$title" "$text" "$@") || return 1
      ;;
  esac
  echo "$out"
}

# ============================================================ lista de marcas
ui_checklist() {
  local title="$1" text="$2"; shift 2
  local out=""
  case "$UI_ENGINE" in
    dialog)
      local -a args=()
      while (($# >= 3)); do args+=("$1" "$2" "$3"); shift 3; done
      out=$(dialog --stdout --backtitle "$BACKTITLE" --title "$title" \
            --checklist "$text" 0 0 0 "${args[@]}") || return 1
      ;;
    whiptail)
      local -a args=()
      while (($# >= 3)); do args+=("$1" "$2" "$3"); shift 3; done
      if [[ "$_WHIPTAIL_STDOUT" == true ]]; then
        out=$(whiptail --stdout --backtitle "$BACKTITLE" --title "$title" \
              --checklist "$text" 0 0 0 "${args[@]}") || return 1
      else
        out=$(whiptail --backtitle "$BACKTITLE" --title "$title" \
              --checklist "$text" 0 0 0 "${args[@]}" 3>&1 1>&2 2>&3) || return 1
      fi
      ;;
    texto)
      out=$(texto_checklist "$title" "$text" "$@") || return 1
      ;;
  esac
  # dialog/whiptail devuelven los tags entre comillas: "a" "b"
  echo "$out" | tr -d '"'
}

# ============================================================ confirmación
# Uso: ui_yesno "Título" "Texto" ["EtiquetaSí"] ["EtiquetaNo"]
# (las etiquetas solo se aplican al motor dialog)
ui_yesno() {
  local title="$1" text="$2" ylabel="${3:-Sí}" nlabel="${4:-No}" resp
  case "$UI_ENGINE" in
    dialog)
      dialog --stdout --backtitle "$BACKTITLE" --title "$title" \
        --yes-label "$ylabel" --no-label "$nlabel" --yesno "$text" 0 0
      ;;
    whiptail) whiptail --backtitle "$BACKTITLE" --title "$title" --yesno "$text" 0 0 ;;
    texto)
      read -rp "${text} [s/N]: " resp
      [[ "${resp,,}" =~ ^(s|si|y|yes)$ ]]
      ;;
  esac
}

# ============================================================ aviso (msgbox)
ui_alert() {
  local title="${2:-Aviso}" text="$1"
  case "$UI_ENGINE" in
    dialog)   dialog --stdout --backtitle "$BACKTITLE" --title "$title" --msgbox "$text" 0 0 ;;
    whiptail) whiptail --backtitle "$BACKTITLE" --title "$title" --msgbox "$text" 0 0 ;;
    texto)
      echo
      echo -e "${C_YELLOW}${text}${C_RESET}"
      read -rp "Pulse Enter para continuar..." _
      ;;
  esac
}

# ============================================================ mensaje plano
ui_info() {
  echo
  echo -e "${C_CYAN}${C_BOLD}== $1 ==${C_RESET}"
  echo
}

ui_pause() {
  echo
  read -rp "${C_DIM}Pulse Enter para continuar...${C_RESET}" _
}

ui_step() {
  echo -e "  ${C_GREEN}->${C_RESET} $1"
}

# ============================================================ motor de texto
# Selectores interactivos con cursor (flechas ↑/↓), tema monocromo.
# Funcionan sin dialog/whiptail y también como selector rápido de software.

# ------------------------------------------------------------ utilidades TUI
_term_cols() { tput cols 2>/dev/null || echo 80; }
_term_rows() { tput lines 2>/dev/null || echo 24; }

_sel_enter() { printf '\e[?25l' >&2; stty -echo 2>/dev/null; }
_sel_leave() { printf '\e[?25h' >&2; stty echo 2>/dev/null; }

# Altura útil para la lista de ítems (filas visibles a la vez)
_sel_height() {
  local h=$(( $(_term_rows) - 7 ))
  ((h < 6)) && h=6
  echo "$h"
}

# Lee una tecla y la traduce: up/down/right/left/space/enter/esc/eof/letra
_key_read() {
  local k k2 k3
  if ! IFS= read -rsN1 k; then echo "eof"; return; fi
  case "$k" in
    $'\e')
      if IFS= read -rsN1 -t 0.05 k2 2>/dev/null; then
        case "$k2" in
          '['|'O')
            if IFS= read -rsN1 -t 0.05 k3 2>/dev/null; then
              case "$k3" in
                A) echo "up" ;;
                B) echo "down" ;;
                C) echo "right" ;;
                D) echo "left" ;;
                H) echo "home" ;;
                F) echo "end" ;;
                Z) echo "shift_tab" ;;
                *) echo "esc" ;;
              esac
            else
              echo "esc"
            fi
            ;;
          *) echo "esc" ;;
        esac
      else
        echo "esc"
      fi
      ;;
    $' ') echo "space" ;;
    $'\t') echo "tab" ;;
    $'\n'|$'\r') echo "enter" ;;
    *) echo "$k" ;;
  esac
}

# Limpia pantalla y pinta el encabezado (título + texto) en stderr
_draw_header() {
  printf '\e[2J\e[H' >&2
  printf '\e[1m%s\e[0m\n' "$1" >&2
  [[ -n "$2" ]] && printf '\e[2m  %s\e[0m\n\n' "$2" >&2
  printf '\n' >&2
}

# ------------------------------------------------- menú con cursor (ui_menu)
texto_menu() {
  local title="$1" text="$2"; shift 2
  local -a tags=() labels=()
  while (($# >= 2)); do tags+=("$1"); labels+=("$2"); shift 2; done
  local n=${#tags[@]} cur=0 top=0 height key jump
  ((n == 0)) && return 1
  height=$(_sel_height)
  _sel_enter
  trap '_sel_leave' EXIT
  while true; do
    _draw_header "$title" "$text"
    local j
    for ((j=top; j<n && j<top+height; j++)); do
      if (( j == cur )); then
        printf '\e[7m  %2d) %s  \e[0m\n' "$((j+1))" "${labels[j]}" >&2
      else
        printf '  %2d) %s\n' "$((j+1))" "${labels[j]}" >&2
      fi
    done
    if ((top + height < n)); then
      printf '\e[2m  … (%d más) ↓\e[0m\n' "$((n - top - height))" >&2
    fi
    printf '\n  \e[2m↑/↓ mover · Enter seleccionar · 0 o q salir\e[0m\n' >&2
    key=$(_key_read)
    case "$key" in
      up)   ((cur > 0)) && cur=$((cur - 1)) ;;
      down) ((cur < n - 1)) && cur=$((cur + 1)) ;;
      enter) break ;;
      esc|q|eof|'0') cur=-1; break ;;
      [1-9])
        jump=$((10#$key - 1))
        ((jump >= 0 && jump < n)) && cur=$jump
        ;;
    esac
    # mantener visible el cursor (viewport)
    ((cur < top)) && top=$cur
    if ((cur >= top + height)); then top=$((cur - height + 1)); fi
  done
  _sel_leave
  trap - EXIT
  if ((cur >= 0)); then echo "${tags[cur]}"; return 0; fi
  return 1
}

# ------------------------------------------- checklist con cursor (ui_checklist)
texto_checklist() {
  local title="$1" text="$2"; shift 2
  local -a tags=() descs=() mark=()
  local i=0
  while (($# >= 3)); do
    tags+=("$1"); descs+=("$2"); mark[i]=0
    [[ "$3" == "on" ]] && mark[i]=1
    i=$((i + 1)); shift 3
  done
  local n=${#tags[@]} cur=0 top=0 height key jump
  ((n == 0)) && return 1
  height=$(_sel_height)
  _sel_enter
  trap '_sel_leave' EXIT
  while true; do
    _draw_header "$title" "$text"
    local j st
    for ((j=top; j<n && j<top+height; j++)); do
      st=" "; ((mark[j] == 1)) && st="X"
      if (( j == cur )); then
        printf '\e[7m  [%s] %2d) %-14s %s  \e[0m\n' "$st" "$((j + 1))" "${tags[j]}" "${descs[j]}" >&2
      else
        printf '  [%s] %2d) %-14s %s\n' "$st" "$((j + 1))" "${tags[j]}" "${descs[j]}" >&2
      fi
    done
    if ((top + height < n)); then
      printf '\e[2m  … (%d más) ↓\e[0m\n' "$((n - top - height))" >&2
    fi
    printf '\n  \e[2m↑/↓ mover · Espacio marcar · Enter continuar · q salir\e[0m\n' >&2
    key=$(_key_read)
    case "$key" in
      up)   ((cur > 0)) && cur=$((cur - 1)) ;;
      down) ((cur < n - 1)) && cur=$((cur + 1)) ;;
      space) ((mark[cur] = 1 - mark[cur])) ;;
      enter) break ;;
      esc|q|eof) cur=-1; break ;;
      [1-9])
        jump=$((10#$key - 1))
        ((jump >= 0 && jump < n)) && cur=$jump
        ;;
    esac
    ((cur < top)) && top=$cur
    if ((cur >= top + height)); then top=$((cur - height + 1)); fi
  done
  _sel_leave
  trap - EXIT
  if ((cur < 0)); then return 1; fi
  local -a out=()
  for ((j=0; j<n; j++)); do
    ((mark[j] == 1)) && out+=("${tags[j]}")
  done
  echo "${out[*]}"
}

# ----------------------------------- checklist con cursor + descripción (popup)
# Igual que texto_checklist pero muestra la descripción del ítem resaltado
# al pulsar TAB (o Shift+TAB, o i/d). La ventana de descripción es mínima y
# se cierra al pulsar ↑/↓ o Esc.
ui_checklist_sel() {
  local title="$1" text="$2"; shift 2
  local -a tags=() descs=() mark=()
  local i=0
  while (($# >= 3)); do
    tags+=("$1"); descs+=("$2"); mark[i]=0
    [[ "$3" == "on" ]] && mark[i]=1
    i=$((i + 1)); shift 3
  done
  local n=${#tags[@]} cur=0 top=0 height key jump
  ((n == 0)) && return 1
  height=$(_sel_height)
  _sel_enter
  trap '_sel_leave' EXIT
  while true; do
    _draw_header "$title" "$text"
    local j st
    for ((j=top; j<n && j<top+height; j++)); do
      st=" "; ((mark[j] == 1)) && st="X"
      if (( j == cur )); then
        printf '\e[7m  [%s] %2d) %-16s %s  \e[0m\n' "$st" "$((j + 1))" "${tags[j]}" "${descs[j]}" >&2
      else
        printf '  [%s] %2d) %-16s %s\n' "$st" "$((j + 1))" "${tags[j]}" "${descs[j]}" >&2
      fi
    done
    if ((top + height < n)); then
      printf '\e[2m  … (%d más) ↓\e[0m\n' "$((n - top - height))" >&2
    fi
    printf '\n  \e[2m↑/↓ mover · Espacio marcar · TAB descripción · Enter continuar · q salir\e[0m\n' >&2

    # si acabamos de cerrar el popup de descripción, se reutiliza esa tecla
    [[ -n "$key" ]] || key=$(_key_read)
    case "$key" in
      i|d|h|tab|shift_tab)
        key=$(_draw_info "${tags[cur]}")
        continue
        ;;
      close) : ;;
      up)   ((cur > 0)) && cur=$((cur - 1)) ;;
      down) ((cur < n - 1)) && cur=$((cur + 1)) ;;
      space) ((mark[cur] = 1 - mark[cur])) ;;
      enter) break ;;
      esc|q|eof) cur=-1; break ;;
      [1-9])
        jump=$((10#$key - 1))
        ((jump >= 0 && jump < n)) && cur=$jump
        ;;
    esac
    ((cur < top)) && top=$cur
    if ((cur >= top + height)); then top=$((cur - height + 1)); fi
    key=""
  done
  _sel_leave
  trap - EXIT
  if ((cur < 0)); then return 1; fi
  local -a out=()
  for ((j=0; j<n; j++)); do
    ((mark[j] == 1)) && out+=("${tags[j]}")
  done
  echo "${out[*]}"
}

# Popup minimalista con la descripción del ítem. Se cierra con cualquier
# tecla; devuelve la tecla pulsada para que el bucle la procese (↑/↓ mueven).
# TAB de nuevo solo cierra (devuelve "close" para no reabrir el popup).
_draw_info() {
  local tag="$1"
  # Ojo: se separan los `local` porque expandir una matriz asociativa
  # con el valor de otra variable en un mismo `local a=... b="${arr[$a]:-}"`
  # provoca "subíndice de matriz incorrecto" en bash.
  local desc="${NAV_DESC[$tag]:-}"
  local cols rows w l t wrapped
  cols=$(_term_cols); rows=$(_term_rows)
  w=$((cols - 12)); ((w < 28)) && w=28
  ((w > 78)) && w=78
  l=$(( (cols - w) / 2 )); ((l < 2)) && l=2
  t=$((rows - 7)); ((t < 2)) && t=2
  [[ -n "$desc" ]] || desc="Sin descripción disponible para «$tag»."
  mapfile -t wrapped <<< "$(printf '%s' "$desc" | fold -s -w $((w - 4)) | head -n 2)"
  tput cup "$t" "$l" >&2
  printf '╔' >&2
  printf '═%.0s' $(seq 1 $((w - 2))) >&2
  printf '╗' >&2
  tput cup $((t + 1)) "$l" >&2
  printf '║ %-*s ║' "$((w - 4))" "${wrapped[0]:-}" >&2
  tput cup $((t + 2)) "$l" >&2
  printf '║ %-*s ║' "$((w - 4))" "${wrapped[1]:-}" >&2
  tput cup $((t + 3)) "$l" >&2
  printf '╚' >&2
  printf '═%.0s' $(seq 1 $((w - 2))) >&2
  printf '╝' >&2
  tput cup $((t + 4)) "$l" >&2
  printf '\e[2m  ↑/↓ o Esc para cerrar\e[0m' >&2
  local close_key
  close_key=$(_key_read)
  case "$close_key" in
    tab|shift_tab) echo "close" ;;
    *) echo "$close_key" ;;
  esac
}
