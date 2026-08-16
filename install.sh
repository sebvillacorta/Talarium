#!/usr/bin/env bash
# =============================================================================
# Talarium - instalador (creado por sebvillacorta / RevOst)
# Clona Talarium en ~/.local/share/talarium y crea el lanzador ~/.local/bin/talarium
# Uso:  curl -fsSL https://raw.githubusercontent.com/sebvillacorta/Talarium/main/install.sh | bash
# =============================================================================
set -euo pipefail

REPO="${TALARIUM_REPO:-https://github.com/sebvillacorta/Talarium.git}"
BRANCH="${TALARIUM_BRANCH:-main}"
DEST="${TALARIUM_HOME:-$HOME/.local/share/talarium}"
BIN_DIR="${TALARIUM_BIN:-$HOME/.local/bin}"
LINK="$BIN_DIR/talarium"

say() { printf '\033[1;37m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mError:\033[0m %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null 2>&1 || die "se necesita 'git' para instalar Talarium."

say "Clonando Talarium ($BRANCH) en $DEST"
if [[ -d "$DEST/.git" ]]; then
  git -C "$DEST" fetch origin "$BRANCH" && git -C "$DEST" reset --hard "origin/$BRANCH"
else
  mkdir -p "$(dirname "$DEST")"
  git clone --depth 1 --branch "$BRANCH" "$REPO" "$DEST"
fi

say "Creando lanzador en $LINK"
mkdir -p "$BIN_DIR"
ln -sf "$DEST/talarium.sh" "$LINK"
chmod +x "$DEST/talarium.sh"

if ! command -v dialog >/dev/null 2>&1; then
  say "Sugerencia: instala 'dialog' para la interfaz completa"
fi

say "¡Talarium instalado!"
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    # shellcheck disable=SC2016  # el $PATH literal es lo que se imprime al usuario
    printf 'Añade %s a tu PATH:\n   echo '\''export PATH="%s:$PATH"'\'' >> ~/.bashrc\n   source ~/.bashrc\n' "$BIN_DIR" "$BIN_DIR"
    ;;
esac
printf '\nEjecuta:  talarium\n'