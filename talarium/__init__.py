"""Talarium - Gestor de sistema para Linux (Python 3).

Estructura modular:

- cli/app        : punto de entrada y ciclo de vida (señales, limpieza sudo)
- core           : detección del sistema, gestores de paquetes, catálogos
- ui             : backends de interfaz (dialog / whiptail / texto)
- modules        : funcionalidad (software, sistema, visual, consejos, backup)
"""

__version__ = "1.0.0"
PROJECT_NAME = "Talarium"
AUTHOR = "sebvillacorta (RevOst)"
