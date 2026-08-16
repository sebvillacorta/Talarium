#!/usr/bin/env bash
# =============================================================================
# Talarium - instalador
# Clona Talarium en ~/.local/share/talarium y crea el lanzador ~/.local/bin/talarium
# Uso:  curl -fsSL https://raw.githubusercontent.com/sebvillacorta/Talarium/main/install.sh | bash
#
# Notas:
#  - Talarium es un paquete Python 3; NO depende de un bit de ejecución para
#    funcionar (basta con 'python3 -m talarium'), pero el lanzador sí lo usa.
#  - Tras la instalación se pregunta SI/NO si se desea conceder el permiso de
#    ejecución al lanzador. Si respondes NO, se indica cómo hacerlo después.
# =============================================================================
set -euo pipefail

REPO="${TALARIUM_REPO:-https://github.com/sebvillacorta/Talarium.git}"
BRANCH="${TALARIUM_BRANCH:-main}"
DEST="${TALARIUM_HOME:-$HOME/.local/share/talarium}"
BIN_DIR="${TALARIUM_BIN:-$HOME/.local/bin}"
LINK="$BIN_DIR/talarium"

say() { printf '\033[1;37m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mError:\033[0m %s\n' "$*" >&2; exit 1; }

# ----------------------------------------------------------------- requisitos
command -v git >/dev/null 2>&1 || die "se necesita 'git' para instalar Talarium."

PY=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)' 2>/dev/null; then
    PY="$cand"; break
  fi
done
[[ -n "$PY" ]] || die "se necesita Python 3.8+ para ejecutar Talarium."

# ------------------------------------------------------------------- clonado
say "Clonando Talarium ($BRANCH) en $DEST"
if [[ -d "$DEST/.git" ]]; then
  git -C "$DEST" fetch origin "$BRANCH" && git -C "$DEST" reset --hard "origin/$BRANCH"
else
  mkdir -p "$(dirname "$DEST")"
  git clone --depth 1 --branch "$BRANCH" "$REPO" "$DEST"
fi

say "Verificando el paquete Python..."
"$PY" -m compileall -q "$DEST/talarium" || die "el código Python no compila; revisa la instalación."

say "Creando lanzador en $LINK"
mkdir -p "$BIN_DIR"
ln -sf "$DEST/bin/talarium" "$LINK"

# ------------------------------------------------- permiso de ejecución (SÍ/NO)
if [[ -x "$LINK" ]]; then
  say "Permiso de ejecución: ya estaba concedido en $LINK"
else
  printf '\n\033[1m¿Conceder permiso de ejecución al lanzador %s?\033[0m [s/N] ' "$LINK"
  read -r ans
  case "${ans:-n}" in
    s|S|y|Y|si|SI|yes|YES)
      chmod +x "$LINK" "$DEST/bin/talarium"
      say "Permiso de ejecución concedido."
      ;;
    *)
      say "OK, no se concedió el permiso. El programa sigue funcionando con:"
      printf '   %s -m talarium --doctor   (diagnóstico)\n' "$PY"
      printf '   %s -m talarium            (menú interactivo)\n' "$PY"
      printf 'Para concederlo más tarde:\n   chmod +x %s\n' "$LINK"
      ;;
  esac
fi

# -------------------------------------------------------------------- consejos
if ! command -v dialog >/dev/null 2>&1; then
  say "Sugerencia: instala 'dialog' para la interfaz completa"
fi

say "¡Talarium instalado!"
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    printf 'Añade %s a tu PATH:\n   echo '\''export PATH="%s:$PATH"'\'' >> ~/.bashrc\n   source ~/.bashrc\n' "$BIN_DIR" "$BIN_DIR"
    ;;
esac
printf '\nEjecuta:  talarium\n'
