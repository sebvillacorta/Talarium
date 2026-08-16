<div align="center">

# Talarium

**Gestor de sistema para Linux · 100% TUI · Tema monocromo**

![version](https://img.shields.io/badge/version-1.0.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![shell](https://img.shields.io/badge/lenguaje-Bash-4EAA25)
![ui](https://img.shields.io/badge/interfaz-dialog%20%2F%20whiptail%20%2F%20texto-lightgrey)

```
 ╔══════════════════════════════════════════════════════════════════════════════╗
 ║                                                                              ║
 ║       ████████╗ █████╗ ██╗      █████╗ ██████╗ ██╗██╗   ██╗███╗   ███╗       ║
 ║       ╚══██╔══╝██╔══██╗██║     ██╔══██╗██╔══██╗██║██║   ██║████╗ ████║       ║
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
 ║  segun tu equipo y respalda tu configuracion. Todo desde la terminal,        ║
 ║  100% TUI. Nada se instala sin tu confirmacion.                              ║
 ╚══════════════════════════════════════════════════════════════════════════════╝
```

**Creado por [sebvillacorta](https://github.com/sebvillacorta) (alias RevOst)**

</div>

---

Talarium es un gestor de sistema para Linux que se maneja **íntegramente desde la
terminal**. Instala software por categorías (incluidas herramientas descargadas
de releases oficiales de GitHub), limpia paquetes innecesarios, ajusta la
interfaz gráfica, recomienda optimizaciones según tu equipo y respalda tu
configuración. Todo con tema **monocromo** y sin salir del terminal.

## Características

- **Software por categorías** — listas editables por gestor de paquetes
  (`config/software/*.conf`), con perfiles para informática, desarrollo,
  creación de contenido, diseño gráfico, oficina y más.
- **Selector con cursor** — en las ventanas de selección se navega con
  las flechas `↑/↓` y se marca con `Espacio`. Pulsando `TAB` sobre un paquete
  se abre una ventana mínima con su descripción (se cierra con `↑/↓` o `Esc`).
  También funcionan `Shift+TAB` y la tecla `i`.
- **Flatpak** — los paquetes con prefijo `flatpak:ID` se instalan desde
  Flathub (`config/software/*.conf`), ideal para apps actualizadas sin
  tocar las dependencias del sistema.
- **Herramientas desde GitHub** — descarga e instala binarios de los
  *releases* oficiales de GitHub (eza, bat, lazygit, gh, Obsidian, VS Code…),
  eligiendo el formato correcto según tu gestor (`.rpm`, `.deb`, `.pkg.tar`).
- **Desbloat y mantenimiento** — paquetes huérfanos, cachés, journal, limpieza
  de `dnf`/`apt`/`pacman`/`zypper`/`xbps`.
- **Ajustes visuales** — GNOME, KDE y XFCE: fuentes, tema, extensiones, TRIM,
  instalación de Zsh.
- **Recomendaciones** — según tu distro, RAM, CPU y GPU (incluye drivers
  NVIDIA propietarios por distro).
- **Copias de seguridad** — respaldo y restauración de configuración.
- **Seguridad por diseño** — nada se instala ni se elimina sin tu
  confirmación; `sudo` solo se pide cuando la operación lo requiere.

## Sistemas soportados

| Distribución | Gestor | Estado |
|---|---|---|
| Fedora / RHEL / CentOS / Rocky / AlmaLinux / Nobara | `dnf` | ✅ |
| Arch / Manjaro / EndeavourOS | `pacman` (+AUR) | ✅ |
| Debian / Ubuntu / Mint | `apt` | ✅ |
| openSUSE | `zypper` | ✅ |
| Void | `xbps` | ✅ |

## Instalación

**Con una línea** (requiere `git`):

```bash
curl -fsSL https://raw.githubusercontent.com/sebvillacorta/Talarium/main/install.sh | bash
```

**Manual**:

```bash
git clone https://github.com/sebvillacorta/Talarium.git
cd Talarium
./talarium.sh
```

Instala en `~/.local/share/talarium` y crea el lanzador `~/.local/bin/talarium`
(que deberá estar en tu `PATH`).

## Uso

```text
./talarium.sh            Abre el menú interactivo
./talarium.sh --doctor   Diagnóstico del sistema
./talarium.sh --help     Ayuda
```

Panel principal:

1. **Software** — instalar / desinstalar por categorías y desde GitHub
2. **Sistema** — limpieza, desbloat y mantenimiento
3. **Visual** — ajustes gráficos e interfaz
4. **Consejos** — recomendaciones según tu equipo
5. **Backup** — copia de seguridad y restauración

## Configuración

Las listas de paquetes son simples archivos de texto:

```text
categoria: paquete1 paquete2 flatpak:com.ejemplo.App
```

- `config/software/dnf.conf` · `apt.conf` · `pacman.conf` · `zypper.conf`
  — paquetes por categoría y gestor. El prefijo `flatpak:` indica que el
  paquete se instala desde Flathub.
- `config/software/descriptions.conf` — descripciones para el selector con
  cursor, con formato `etiqueta|Nombre visible|Descripción breve`.
- `config/software/github.conf` — herramientas de GitHub, con formato:

  ```text
  herramienta|patrón_del_asset|URL_del_release|binario_destino(opcional)
  ```

  El asset se elige automáticamente según el gestor (`.rpm`, `.deb`,
  `.pkg.tar.*`).

## Seguridad

- Nada se instala ni se elimina sin confirmación explícita.
- `sudo` se solicita solo cuando hace falta y cada operación lo valida.
- Las herramientas de GitHub se descargan únicamente de los *releases*
  oficiales de cada proyecto.

## Estructura del proyecto

```text
talarium.sh               Entrada principal (menú, splash, despedida)
lib/
  core.sh                 Detección de sistema y gestores de paquetes
  ui.sh                   Interfaz (dialog / whiptail / texto) y splash
  packages.sh             Instalación por categorías y desde GitHub
  debloat.sh              Limpieza y desbloat
  tweaks.sh               Ajustes visuales
  recommend.sh            Recomendaciones según hardware
  backup.sh               Copias de seguridad
config/
  software/*.conf         Listas de paquetes (editables)
  software/descriptions.conf  Descripciones del selector con cursor
  debloat/*.conf          Listas de bloat (editables)
```

## Contribuir

Las aportaciones son bienvenidas: abre un *issue* o un *pull request*.
Los scripts se validan con `bash -n` y [ShellCheck](https://www.shellcheck.net/)
en cada push mediante GitHub Actions.

## Licencia

[MIT](LICENSE) © 2026 sebvillacorta (RevOst)