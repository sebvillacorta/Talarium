"""Punto de entrada por línea de comandos.

Uso:
    talarium                 -> menú interactivo
    talarium --doctor        -> diagnóstico del sistema
    talarium --backend texto -> forzar un backend de interfaz
    talarium --help          -> ayuda
    talarium --version       -> versión
"""

import argparse
import sys

from . import __version__


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="talarium",
        description="Gestor de sistema para Linux (software, limpieza, visual, consejos, backup).",
    )
    p.add_argument("--doctor", action="store_true",
                   help="muestra el diagnóstico del sistema y sale")
    p.add_argument("--backend", choices=["dialog", "whiptail", "texto"],
                   help="fuerza un backend de interfaz")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv=None) -> int:
    args = _parser().parse_args(argv)

    if args.doctor:
        from .app import run_doctor
        try:
            return run_doctor()
        except Exception as exc:  # noqa: BLE001
            print(f"Error en el diagnóstico: {exc}")
            return 1

    from .app import TalariumApp, ensure_dialog_hint
    try:
        app = TalariumApp(ui_force=args.backend or "")
        return app.run()
    except KeyboardInterrupt:
        print("\n  Interrumpido por el usuario.")
        return 130
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception as exc:  # noqa: BLE001 - último recurso: mensaje claro
        from .errors import TalariumError
        msg = str(exc) or exc.__class__.__name__
        print(f"\nError: {msg}")
        if isinstance(exc, TalariumError):
            print("Consulta 'talarium --doctor' para más información.")
        return 1
    finally:
        ensure_dialog_hint()


if __name__ == "__main__":
    sys.exit(main())
