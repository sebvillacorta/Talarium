<div align="center">

# Talarium

**Gestor de sistema para Linux · 100% TUI · Tema monocromo**

![version](https://img.shields.io/badge/version-1.0.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![language](https://img.shields.io/badge/lenguaje-Python%203-3776AB)
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
 ║       Gestor de sistema para Linux  ·  v1.0.0  ·  100% Python                ║
 ║            Motor: dialog - whiptail - texto   ·   Tema: monocromo            ║
 ║                                                                              ║
 ╚══════════════════════════════════════════════════════════════════════════════╝
```

**Creado por [sebvillacorta](https://github.com/sebvillacorta) (alias RevOst)**

</div>

---

Talarium es un gestor de sistema para Linux que se maneja **íntegramente desde la
terminal**. Está escrito en **Python 3** (sin dependencias externas) y mantiene
los datos de configuración en simples archivos de texto editables. Instala
software por categorías (incluidas herramientas descargadas de releases
oficiales de GitHub), limpia paquetes innecesarios, ajusta la interfaz gráfica,
recomienda optimizaciones según tu equipo y respalda tu configuración.

## Características

- **Software por categorías** — listas editables por gestor de paquetes
  (`config/software/*.conf`), con perfiles para informática, desarrollo,
  creación de contenido, diseño gráfico, oficina y más.
- **Flatpak** — los paquetes con prefijo `flatpak:ID` se instalan desde Flathub.
- **Herramientas desde GitHub** — descarga e instala binarios de los *releases*
  oficiales de GitHub (eza, bat, lazygit, gh, Obsidian, VS Code…), eligiendo el
  formato según tu gestor (`.rpm`, `.deb`, `.pkg.tar`, AppImage, tar.gz…).
- **Desbloat y mantenimiento** — paquetes huérfanos, cachés, journal, limpieza
  de `dnf`/`apt`/`pacman`/`zypper`/`xbps`.
- **Ajustes visuales** — GNOME, KDE y XFCE: fuentes, tema, extensiones, TRIM,
  instalación de Zsh.
- **Recomendaciones** — según tu distro, RAM, CPU y GPU (incluye drivers
  NVIDIA propietarios por distro).
- **Copias de seguridad** — respaldo y restauración de configuración.
- **Seguridad por diseño** — nada se instala ni se elimina sin tu confirmación;
  la contraseña de sudo se pide una sola vez por sesión, vive **sólo en
  memoria** y se borra al salir (`sudo -k`).

## Sistemas soportados

| Distribución | Gestor | Estado |
|---|---|---|
| Fedora / RHEL / CentOS / Rocky / AlmaLinux / Nobara | `dnf` | ✅ |
| Arch / Manjaro / EndeavourOS | `pacman` (+AUR) | ✅ |
| Debian / Ubuntu / Mint | `apt` | ✅ |
| openSUSE | `zypper` | ✅ |
| Void | `xbps` | ✅ |

## Requisitos

- **Python 3.8+** (presente por defecto en todas las distros listadas).
- Opcional: `dialog` (mejor interfaz), `git` (para el instalador),
  `curl` (descargas desde GitHub).

## Instalación

**Con una línea** (requiere `git`):

```bash
curl -fsSL https://raw.githubusercontent.com/sebvillacorta/Talarium/main/install.sh | bash
```

El instalador clona el proyecto en `~/.local/share/talarium`, crea el lanzador
`~/.local/bin/talarium` y, tras instalar, te pregunta **SÍ/NO** si quieres
conceder el permiso de ejecución al lanzador antes de invitarte a usarlo.
Si respondes que no, te indica cómo ejecutarlo sin permiso.

**Manual** (sin instalador):

```bash
git clone https://github.com/sebvillacorta/Talarium.git
cd Talarium
python3 -m talarium          # menú interactivo
```

**Instalar como paquete** (opcional):

```bash
python3 -m pip install .     # crea el comando "talarium" en tu PATH
```

## Uso

```text
talarium                 Abre el menú interactivo
talarium --doctor        Diagnóstico del sistema
talarium --backend texto Fuerza interfaz de texto plano
talarium --help          Ayuda
talarium --version       Versión
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
- `config/software/descriptions.conf` — descripciones breves de aplicaciones,
  con formato `etiqueta|Nombre visible|Descripción`.
- `config/software/github.conf` — herramientas de GitHub, con formato:

  ```text
  herramienta|patrón_del_asset|URL_del_release|binario_destino(opcional)
  ```

  El asset se elige automáticamente según el gestor (`.rpm`, `.deb`,
  `.pkg.tar.*`).

## Seguridad

- Nada se instala ni se elimina sin confirmación explícita.
- La contraseña de sudo se pide una vez por sesión y se guarda **sólo en
  memoria** (`bytearray`); al salir se ejecuta `sudo -k` y se sobrescribe el
  búfer. Nunca se escribe en disco, logs ni variables de entorno.
- Cada operación privilegiada refresca la sesión de sudo de forma silenciosa.
- Las herramientas de GitHub se descargan únicamente de los *releases*
  oficiales de cada proyecto.

## Estructura del proyecto

```text
bin/talarium               Lanzador (bootstrap de Python)
install.sh                 Instalador (pregunta SÍ/NO el permiso de ejecución)
pyproject.toml             Metadatos y entry point (pip install)
talarium/
  cli.py                   Argumentos CLI (--doctor, --backend, ...)
  app.py                   Ciclo de vida: menú, señales, limpieza de sudo
  sudo.py                  SudoSession: contraseña en memoria + sudo -k al salir
  core/                    Detección, runner, catálogos, gestores, GitHub
  ui/                      Backends: dialog / whiptail / texto
  modules/                 Software, sistema, visual, consejos, backup
config/
  software/*.conf          Listas de paquetes (editables)
  software/descriptions.conf  Descripciones de aplicaciones
  debloat/*.conf           Listas de bloat (editables)
  theme/dialog.mono        Tema monocromo para dialog
docs/architecture.md       Arquitectura y análisis de fallas
```

Ver [docs/architecture.md](docs/architecture.md) para el análisis detallado de
las fallas cubiertas y las decisiones de diseño.

## Contribuir

Las aportaciones son bienvenidas: abre un *issue* o un *pull request*.
El código se valida con `python3 -m compileall` y se revisa con análisis
estático antes de cada push.

## Licencia

[MIT](LICENSE) © 2026 sebvillacorta (RevOst)
