"""Banner ASCII de bienvenida (impreso en la pantalla real, antes del TUI)."""

from talarium import __version__

BANNER = r"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║       ████████╗ █████╗ ██╗      █████╗ ██████╗ ██╗██╗   ██╗███╗   ███╗       ║
║       ╚══██╔══╝██╔══██╗██║     ██╔══██╗██╔══██╗██║██╗   ██║████╗ ████║       ║
║          ██║   ███████║██║     ███████║██████╔╝██║██║   ██║██╔████╔██║       ║
║          ██║   ██╔══██║██║     ██╔══██║██╔══██╗██║██║   ██║██║╚██╔╝██║       ║
║          ██║   ██║  ██║███████╗██║  ██║██║  ██║██║╚██████╔╝██║ ╚═╝ ██║       ║
║          ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝     ╚═╝       ║
║                                                                              ║
║     Gestor de sistema para Linux · v""" + f"{__version__}" + r""" · 100% Python    ║
║             Interfaz: dialog · whiptail · texto   ·  Tema: monocromo        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

FOOTER = """Talarium: gestor de sistema para Linux. Creado por sebvillacorta (alias RevOst).
Instala software por categorías, limpia paquetes innecesarios, ajusta la
interfaz gráfica, recomienda optimizaciones según tu equipo y respalda tu
configuración. Nada se instala sin tu confirmación y la contraseña de sudo
se borra de memoria al salir."""
