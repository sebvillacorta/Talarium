# Talarium - Arquitectura recomendada

Talarium dejó de ser un script en bash y ahora es un paquete **Python 3**
modular y tipado, con separación clara de responsabilidades y manejo
explícito de errores. Este documento describe la estructura, las decisiones
de diseño y el análisis de fallas que motivó cada una.

---

## 1. Estructura del proyecto

```
Talarium/
├── bin/talarium              # Lanzador (sólo bootstrap de Python; el programa
│                             #   no depende de bits de ejecución)
├── install.sh                # Instalador: clona, valida el código, crea el
│                             #   lanzador y pregunta SI/NO por el permiso de
│                             #   ejecución antes de invitar a usarlo
├── pyproject.toml            # Metadatos + entry point "talarium" (pip install)
├── talarium/                 # Paquete Python (código del programa)
│   ├── __main__.py           #   python3 -m talarium
│   ├── cli.py                #   Argumentos CLI (--doctor, --backend, --version)
│   ├── app.py                #   Ciclo de vida: bootstrap, menú, señales, salida
│   ├── context.py            #   Inyección de dependencias (Context único)
│   ├── config.py             #   Rutas (root, config, backups)
│   ├── errors.py             #   Jerarquía de excepciones propia
│   ├── sudo.py               #   SudoSession: contraseña en memoria + limpieza
│   ├── core/
│   │   ├── system.py         #   Detección distro/escritorio + info hardware
│   │   ├── runner.py         #   Ejecución de comandos con control de errores
│   │   ├── catalog.py        #   Parser tolerante de config/*.conf
│   │   ├── packagemanager.py #   Abstracción dnf/pacman/apt/zypper/xbps + Flatpak
│   │   └── github.py         #   Instalación desde releases oficiales de GitHub
│   ├── ui/
│   │   ├── base.py           #   API abstracta de interfaz (UI)
│   │   ├── dialog.py         #   Backend dialog/whiptail (tema monocromo)
│   │   ├── text.py           #   Backend de texto plano (último recurso)
│   │   ├── banner.py         #   Arte ASCII de bienvenida
│   │   └── __init__.py       #   Fábrica con degradación automática
│   └── modules/
│       ├── common.py         #   Helpers: sudo seguro, instalar/eliminar mixto
│       ├── software.py       #   Instalar/desinstalar por categorías + GitHub
│       ├── maintenance.py    #   Bloat, huérfanos, cachés, journal, actualizar
│       ├── visual.py         #   Ajustes GNOME/KDE/XFCE, fuentes, zsh, TRIM
│       ├── recommend.py      #   Recomendaciones según hardware y distro
│       └── backup.py         #   Copia de seguridad y restauración
├── config/                   # Datos: catálogos de paquetes, debloat, tema
│   ├── software/*.conf
│   ├── debloat/*.conf
│   └── theme/dialog.mono
└── docs/architecture.md      # Este documento
```

### Por qué Python 3 y no bash
- **Errores tipados**: excepciones propias (`SudoError`, `CommandError`,
  `CatalogError`, `UnsupportedDistro`) en lugar de códigos de salida mágicos.
- **Sin dependencia del bit de ejecución**: `python3 -m talarium` funciona
  aunque ningún archivo tenga `+x`. El lanzador `bin/talarium` sólo localiza
  el intérprete y delega.
- **Gestión segura de memoria** para la contraseña de sudo (`bytearray`,
  sobrescrita al salir).
- **Inyección de dependencias** (`Context`): los módulos no dependen de
  variables globales (como `PM`, `BACKTITLE` en bash), lo que permite probar
  cada pieza por separado.

---

## 2. Modelo de seguridad (contraseña de sudo)

Requisito: *pedir la contraseña una vez por sesión, mantenerla disponible
durante la ejecución y borrarla al salir.*

Implementación en `talarium/sudo.py`:

| Momento | Acción |
|---|---|
| Primera operación privilegiada | `SudoSession.ensure()` pide la contraseña (diálogo o `getpass` sobre `/dev/tty`) y la valida con `sudo -S -p "" -v`. |
| Antes de cada comando privilegiado | Se refresca la marca de tiempo con `sudo -S -v` usando la contraseña en memoria (evita el expirado de 15 min de sudo). |
| Durante la sesión | La contraseña vive **sólo** en un `bytearray` en memoria. Nunca se escribe a disco, logs, entorno ni línea de comandos. |
| Salida normal | `clear()` ejecuta `sudo -k` (invalida la marca de tiempo) y sobrescribe el búfer. |
| Ctrl+C / SIGTERM | Manejador de señales llama a `clear()` antes de salir. |
| `atexit` | Registrado como red de seguridad para cualquier camino de salida. |

Otros casos cubiertos: usuario root (ejecución directa, sin sudo), sudo no
instalado (error accionable), contraseña incorrecta (máx. 3 intentos),
sin terminal interactiva (rechazo explícito, no cuelga).

---

## 3. Análisis de fallas y mitigaciones

| # | Falla posible | Síntoma | Mitigación en Talarium |
|---|---|---|---|
| 1 | **Falta de permiso de ejecución** (el bug original) | `Permiso denegado` al ejecutar `./talarium.sh` | 1) El programa se lanza con `python3 -m talarium`, sin depender de `+x`. 2) `install.sh` pregunta **SÍ/NO** si concede el permiso al lanzador tras instalar, antes de invitar a usarlo; si es NO, imprime los comandos manuales. 3) `bin/talarium` detecta y explica cómo ejecutar sin permiso. |
| 2 | Sin `dialog` ni `whiptail` | Interfaz ausente | Fábrica `create_ui()` degrada dialog → whiptail → texto. En modo texto el menú es numerado y 100% funcional. |
| 3 | Backend TUI roto en runtime | Cuelgue o error de librería | `_BackendFailure` → la fábrica salta al siguiente backend sin tocar el resto. |
| 4 | Sin terminal interactiva | Programas TUI cuelgan en cron/pipe | `config.is_tty()` y backends que leen sólo de `/dev/tty` o devuelven `None` (cancelar). |
| 5 | Contraseña sudo incorrecta | Reintento infinito / mensaje críptico | Máx. 3 intentos con aviso y mensaje claro (grupo wheel/sudo). |
| 6 | Sesión sudo expira (15 min) | Comando largo falla a mitad | `ensure()` refresca la marca con la contraseña en memoria antes de cada operación. |
| 7 | Distro no soportada | Menú con gestor vacío | `require_supported()` aborta con lista de gestores válidos; `--doctor` sigue funcionando. |
| 8 | Gestor de paquetes ausente | `command not found` | Detección de binario (`_pm_binary`) y fallos de OSError convertidos a `CommandError`. |
| 9 | Paquete inexistente en apt/zypper | Transacción completa falla | Reintento individual por paquete (heredado del diseño anterior, ahora tipado). |
| 10 | Red caída al actualizar (dnf/apt) | Código de salida != 0 | Cada operación verifica `returncode` y lo muestra; el usuario decide continuar. |
| 11 | Config `.conf` corrupta o faltante | Parseo roto | `catalog.py` ignora comentarios/blank, valida formato y lanza `CatalogError` con el archivo y la línea. |
| 12 | Ctrl+C a mitad de una instalación | Proceso muerto, sudo sin limpiar | Señales → `clear()` → `sudo -k` + sobrescritura de la contraseña. |
| 13 | Sin `sudo` en el sistema | Todas las operaciones fallan | `SudoSession.available` falso → mensaje específico antes de ejecutar nada. |
| 14 | `dconf` ausente | Backup sin configuración | Se salta silenciosamente esa parte, el resto del backup continúa. |
| 15 | Sin espacio / bloqueo de dpkg | Instalación falla | `CommandError` muestra el comando y el código; no rompe la sesión. |
| 16 | GPU/vendors múltiples | Recomendación errónea | Detección por `lspci` + fallback por `/sys/class/drm`, devuelve "desconocida" si no hay datos. |
| 17 | Python < 3.8 | Módulo no ejecuta | `install.sh` y `bin/talarium` comprueban versión y explican cómo instalar Python. |
| 18 | Ejecución como root | sudo innecesario/confuso | `run()` ejecuta directo cuando `euid==0`; la UI sigue idéntica. |

---

## 4. Decisiones de diseño destacadas

- **`Context` como único objeto de inyección**: cada módulo recibe `ctx` con
  `ui`, `sudo`, `runner`, `catalog`, `pm`, `flatpak`, `distro`. Nada se lee
  de variables de entorno dentro de los módulos.
- **Runner centraliza subprocess**: tiempos límite, captura de salida,
  comprobación de códigos y traducción a `CommandError`. Ningún módulo llama
  a `subprocess` directamente (salvo ajustes gráficos triviales).
- **Catálogos reutilizables**: `config/software/*.conf` no cambió de formato,
  por lo que los datos existentes son válidos tal cual.
- **AUR y Flatpak como prefijos** (`aur:`, `flatpak:`) que resuelve
  `split_packages()`, manteniendo el comportamiento del diseño anterior.
- **UI desacoplada**: los módulos sólo conocen la API abstracta
  (`menu`, `checklist`, `yesno`, `alert`, `password`, `pause`...).

---

## 5. Cómo ampliar

- **Nueva distro**: añade su `ID` en `_SUPPORTED` (core/system.py) y, si
  aplica, su clase de gestor en `packagemanager.py`.
- **Nueva categoría de software**: edita `config/software/<gestor>.conf`.
- **Nuevo backend de UI**: implementa `UI` (ui/base.py) y regístralo en la
  fábrica `create_ui()`.
- **Nueva recomendación**: añade la construcción en `build_recs()` y su
  aplicación en `_apply()` (modules/recommend.py).
