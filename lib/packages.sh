#!/usr/bin/env bash
# =============================================================================
# packages.sh - Instalar / desinstalar software por categorías
# Las listas de paquetes viven en config/software/<gestor>.conf
# =============================================================================

# ---------------------------------------------------------- menú principal
menu_software() {
  local conf="$TALARIUM_CONFIG/software/$PM.conf"
  if [[ ! -r "$conf" ]]; then
    ui_alert "No hay configuración de paquetes para el gestor '${PM:-desconocido}'.\nPuedes crear el archivo: $conf"
    return 1
  fi

  while true; do
    set_backtitle soft
    # construir menú de categorías: "categoria | lista de paquetes"
    local -a items=()
    local cat desc
    while IFS='|' read -r cat desc; do
      [[ -n "$cat" ]] || continue
      items+=("$cat" "${desc:0:58}")
    done < <(awk -F': *' '/^[A-Za-z0-9_-]+:/{ printf "%s|%s\n", $1, $2 }' "$conf")

    if ((${#items[@]} == 0)); then
      ui_alert "La configuración está vacía: $conf"
      return 1
    fi

    items+=("back" "Volver al panel principal")

    # categoría especial: herramientas desde GitHub (si existe el catálogo)
    [[ -r "$TALARIUM_CONFIG/software/github.conf" ]] && \
      items+=("github" "Herramientas desde GitHub (releases oficiales)")

    local sel
    sel=$(ui_menu "Software - categorías" \
      "Lista de paquetes definida para ${PM} en ${DISTRO_NAME} ${DISTRO_VERSION}" \
      "${items[@]}") || return 0
    [[ -n "$sel" && "$sel" != "back" ]] || return 0

    if [[ "$sel" == "github" ]]; then
      show_github
    else
      show_category "$sel"
    fi
  done
}

# ---------------------------------------------------------- detalle categoría
show_category() {
  local cat="$1"
  local conf="$TALARIUM_CONFIG/software/$PM.conf"
  local -a items=()
  local pkgs p

  pkgs=$(awk -F': *' -v c="$cat" '$1==c { print $2 }' "$conf")
  if [[ -z "$pkgs" ]]; then
    ui_alert "La categoría '$cat' no tiene paquetes definidos."
    return
  fi

  for p in $pkgs; do
    if is_installed "$p"; then
      items+=("$p" "[INSTALADO] $p" "off")
    else
      items+=("$p" "[disponible] $p" "on")
    fi
  done

  if ((${#items[@]} == 0)); then
    ui_alert "La categoría '$cat' no tiene paquetes instalables."
    return
  fi

  local chosen
  chosen=$(ui_checklist "Software: $cat" \
    "Marca con ESPACIO los paquetes a instalar (los ya instalados quedan desmarcados)" \
    "${items[@]}") || return
  [[ -n "$chosen" ]] || { ui_alert "No seleccionaste ningún paquete."; return; }

  local act
  act=$(ui_menu "Acción para: $cat" \
    "Paquetes seleccionados: ${chosen}" \
    "install" "INSTALAR los paquetes seleccionados" \
    "remove"  "ELIMINAR los paquetes seleccionados" \
    "back"    "Volver") || return

  case "$act" in
    install)
      ui_yesno "Confirmar instalación" "Se instalarán:\n${chosen}" || return
      ensure_sudo || return 1
      ui_info "Instalando paquetes"
      # shellcheck disable=SC2086  # lista de paquetes separados por espacios
      pm_install $chosen
      ui_pause
      ;;
    remove)
      ui_yesno "Confirmar eliminación" "Se eliminarán:\n${chosen}" || return
      ensure_sudo || return 1
      ui_info "Eliminando paquetes"
      # shellcheck disable=SC2086  # lista de paquetes separados por espacios
      pm_remove $chosen
      ui_pause
      ;;
  esac
}

# ============================================================ GitHub releases
# Instalación de herramientas desde releases oficiales (GitHub o web oficial).
# Catálogo: config/software/github.conf   formato: nombre|patron|url|destino

_gh_dir() { echo "${TMPDIR:-/tmp}/talarium-gh"; }

github_is_installed() {
  command -v "$1" >/dev/null 2>&1
}

# Resuelve la URL del asset ideal para el gestor actual
github_resolve_url() {
  local patron="$1" base="$2"
  local url=""
  if [[ "$base" == *api.github.com* ]]; then
    url=$(curl -fsSL "$base" 2>/dev/null | python3 -c '
import json, sys, re
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(1)
pat = sys.argv[1] if len(sys.argv) > 1 else ""
pm  = sys.argv[2] if len(sys.argv) > 2 else ""
cands = [a["browser_download_url"] for a in data.get("assets", [])
         if re.search(pat, a["name"])]
if not cands:
    sys.exit(1)
# preferencia por gestor: rpm -> dnf/zypper, deb -> apt, pkg.tar.* -> pacman
pref = {"dnf": ".rpm", "zypper": ".rpm", "apt": ".deb",
        "pacman": ".pkg.tar"}.get(pm, "")
if pref:
    for c in cands:
        if c.endswith(pref) or (pref == ".pkg.tar" and ".pkg.tar." in c):
            print(c); sys.exit(0)
print(cands[0])' "$patron" "$PM" 2>/dev/null)
  else
    url="$base"
  fi
  [[ -n "$url" ]] && echo "$url"
}

# Instala una herramienta del catálogo GitHub
github_install() {
  local name="$1" patron="$2" base="$3" dest="${4:-$1}"
  local dir url f ext tmp bin success_msg
  dir="$(_gh_dir)"; mkdir -p "$dir"

  ui_step "Obteniendo enlace de descarga para $name..."
  url=$(github_resolve_url "$patron" "$base")
  if [[ -z "$url" ]]; then
    echo "  No se encontró un asset válido para $name (patrón: $patron)"
    return 1
  fi
  echo "  $url"

  f="$dir/$name.dl"
  ui_step "Descargando $name..."
  if ! curl -fSL "$url" -o "$f" 2>/dev/null; then
    echo "  Error de descarga: no se pudo obtener $name"
    rm -f "$f"
    return 1
  fi

  ext="${f,,}"
  success_msg="$name instalado en ~/.local/bin/$dest"
  case "$ext" in
    *.rpm)
      case "$PM" in
        dnf|zypper) ensure_sudo || return 1; ui_step "Instalando $name (rpm)"; run_pm PM_INSTALL "$f" ;;
        *) echo "  Paquete .rpm no aplica a $PM: instálalo desde el repo oficial." ;;
      esac
      ;;
    *.deb)
      case "$PM" in
        apt) ensure_sudo || return 1; ui_step "Instalando $name (deb)"
             run_sudo dpkg -i "$f" >/dev/null 2>&1 || run_sudo apt-get install -f -y >/dev/null 2>&1 ;;
        *) echo "  Paquete .deb no aplica a $PM." ;;
      esac
      ;;
    *.pkg.tar.zst|*.pkg.tar.xz|*.pkg.tar.gz|*.pkg.tar)
      case "$PM" in
        pacman) ensure_sudo || return 1; ui_step "Instalando $name (pkg.tar)"; run_sudo pacman -U --noconfirm "$f" ;;
        *) echo "  Paquete pkg.tar no aplica a $PM." ;;
      esac
      ;;
    *.appimage)
      ui_step "Instalando $name (AppImage)"
      mkdir -p "$HOME/Applications" "$HOME/.local/bin"
      install -m755 "$f" "$HOME/Applications/$name.AppImage"
      ln -sf "$HOME/Applications/$name.AppImage" "$HOME/.local/bin/$dest"
      ;;
    *.tar.gz|*.tgz|*.tar.xz|*.tar.zst)
      ui_step "Instalando $name (binario)"
      tmp="$dir/$name.x"; rm -rf "$tmp"; mkdir -p "$tmp"
      if ! tar -xf "$f" -C "$tmp" 2>/dev/null; then
        echo "  Error al extraer el archivo."
        rm -rf "$tmp"
        return 1
      fi
      bin=$(find "$tmp" -type f -perm /111 -name "$name" 2>/dev/null | head -1)
      [[ -z "$bin" ]] && bin=$(find "$tmp" -type f -perm /111 2>/dev/null | head -1)
      [[ -z "$bin" ]] && { echo "  No se encontró el binario dentro del archivo."; rm -rf "$tmp"; return 1; }
      mkdir -p "$HOME/.local/bin"
      install -m755 "$bin" "$HOME/.local/bin/$dest"
      ;;
    *.gz)
      ui_step "Instalando $name (binario comprimido)"
      mkdir -p "$HOME/.local/bin"
      if ! gzip -dkf "$f" 2>/dev/null; then
        echo "  Error al descomprimir el archivo."
        return 1
      fi
      install -m755 "${f%.gz}" "$HOME/.local/bin/$dest"
      ;;
    *)
      ui_step "Instalando $name (binario)"
      mkdir -p "$HOME/.local/bin"
      chmod +x "$f" 2>/dev/null || true
      install -m755 "$f" "$HOME/.local/bin/$dest" 2>/dev/null || true
      ;;
  esac
  rm -f "$dir/$name.dl"
  rm -rf "$tmp" 2>/dev/null
  ui_step "$success_msg"
  case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) echo "  OJO: ~/.local/bin no está en PATH. Añádelo con:"
       echo "       echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc" ;;
  esac
}

# Elimina una herramienta instalada desde GitHub
github_remove() {
  local name="$1" dest="${2:-$1}"
  if is_installed "$name"; then
    case "$PM" in
      dnf|zypper|apt|pacman)
        ensure_sudo && run_pm PM_REMOVE "$name" ;;
    esac
  fi
  rm -f "$HOME/.local/bin/$dest" "$HOME/Applications/$name.AppImage"
  echo "  Eliminado: ~/.local/bin/$dest (si existía)"
}

# Menú de herramientas desde GitHub
show_github() {
  local conf="$TALARIUM_CONFIG/software/github.conf"
  [[ -r "$conf" ]] || { ui_alert "No existe el catálogo: $conf"; return 1; }

  local -a items=()
  local name patron base dest
  while IFS='|' read -r name patron base dest; do
    [[ -n "$name" && "$name" != \#* ]] || continue
    if github_is_installed "$name"; then
      items+=("$name" "[INSTALADO] $name" "off")
    else
      items+=("$name" "[descargar] $name (release oficial)" "on")
    fi
  done < "$conf"

  if ((${#items[@]} == 0)); then
    ui_alert "El catálogo está vacío: $conf"
    return 1
  fi

  local chosen
  chosen=$(ui_checklist "Software: GitHub (releases oficiales)" \
    "Descargas desde repositorios oficiales de GitHub / web del proyecto" \
    "${items[@]}") || return
  [[ -n "$chosen" ]] || { ui_alert "No seleccionaste ninguna herramienta."; return; }

  local act
  act=$(ui_menu "Acción para GitHub" \
    "Seleccionadas: ${chosen}" \
    "install" "DESCARGAR e instalar las seleccionadas" \
    "remove"  "Eliminar binario local de las seleccionadas" \
    "back"    "Volver") || return

  command -v curl >/dev/null 2>&1 || { ui_alert "Se necesita 'curl' para descargar."; return; }

  case "$act" in
    install)
      ui_yesno "Confirmar descarga" "Se descargarán e instalarán:\n${chosen}" || return
      for name in $chosen; do
        IFS='|' read -r _ patron base dest < <(awk -F'|' -v n="$name" '$1==n{print; exit}' "$conf")
        [[ -n "$patron" ]] || continue
        github_install "$name" "$patron" "$base" "${dest:-$name}"
      done
      ui_pause
      ;;
    remove)
      for name in $chosen; do
        dest=$(awk -F'|' -v n="$name" '$1==n{print $4; exit}' "$conf")
        github_remove "$name" "${dest:-$name}"
      done
      ui_pause
      ;;
  esac
}
