"""Navegación real: recorre todos los menús y botones del programa.

Ejecuta el programa completo con el backend de texto (entrada por tubería)
y comprueba que cada opción llega a su pantalla y vuelve al panel sin
errores. Las operaciones que requerirían sudo fallan de forma controlada
(aviso de permisos) por no haber terminal interactiva; eso también se
verifica.

Ejecutar desde la raíz del proyecto:
    python3 -m unittest discover -s tests -v
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_app(inputs):
    """Ejecuta el programa con entrada por tubería y un dir de copias aislado."""
    env = dict(os.environ)
    env["TALARIUM_BACKUPS"] = tempfile.mkdtemp(prefix="talarium-backups-test-")
    proc = subprocess.run(
        [sys.executable, "-m", "talarium", "--backend", "texto"],
        input="\n".join(inputs) + "\n",
        capture_output=True, text=True, timeout=60, cwd=str(ROOT), env=env,
    )
    return proc.returncode, proc.stdout + proc.stderr


class NavegacionBase(unittest.TestCase):
    def check(self, inputs, expected, any_of=None):
        rc, out = run_app(inputs)
        self.assertEqual(rc, 0, f"código de salida no 0.\n--- salida ---\n{out}")
        pos = 0
        for needle in expected:
            idx = out.find(needle, pos)  # avanza: las pantallas se repiten al volver
            self.assertNotEqual(idx, -1, f"no aparece: {needle!r}\n--- salida ---\n{out}")
            self.assertGreaterEqual(idx, pos,
                                    f"orden incorrecto para {needle!r}\n--- salida ---\n{out}")
            pos = idx
        if any_of is not None:
            self.assertTrue(any(s in out for s in any_of),
                            f"ninguno de {any_of} aparece\n--- salida ---\n{out}")
        return out


class TestSoftware(NavegacionBase):
    def test_categorias_abre_y_cancela(self):
        self.check(["", "1", "2", "", "16", "7"],
                   ["Software: multimedia", "Software - categorías",
                    "Talarium - Panel principal"])

    def test_github_abre_y_cancela(self):
        self.check(["", "1", "17", "", "16", "7"],
                   ["Software: GitHub (releases oficiales)",
                    "Talarium - Panel principal"])

    def test_instalar_confirmar_y_degradar(self):
        self.check(["", "1", "2", "1", "1", "s", "", "16", "7"],
                   ["Software: multimedia", "Confirmar instalación",
                    "Permisos", "Software - categorías"])

    def test_eliminar_confirmar_y_degradar(self):
        self.check(["", "1", "2", "1", "2", "s", "", "16", "7"],
                   ["Software: multimedia", "Confirmar eliminación",
                    "Permisos", "Software - categorías"])

    def test_desinstalar_abre_y_cancela(self):
        self.check(["", "1", "15", "", "16", "7"],
                   ["Desinstalar herramientas instaladas",
                    "Talarium - Panel principal"])


class TestSistema(NavegacionBase):
    def test_bloat(self):
        out = self.check(["", "2", "1", "", "6", "7"],
                         ["Talarium - Panel principal"],
                         any_of=["Desbloat", "No se detectó software desinstalable"])
        self.assertIn("Desbloat", out)

    def test_huerfanos_sudo_degradado(self):
        self.check(["", "2", "2", "6", "7"],
                   ["Permisos", "Talarium - Panel principal"])

    def test_cache_sudo_degradado(self):
        self.check(["", "2", "3", "6", "7"],
                   ["Permisos", "Talarium - Panel principal"])

    def test_journal_sudo_degradado(self):
        self.check(["", "2", "4", "6", "7"],
                   ["Permisos", "Talarium - Panel principal"])

    def test_actualizar_cancelar(self):
        self.check(["", "2", "5", "n", "6", "7"],
                   ["Actualizar sistema", "Se actualizarán todos los paquetes",
                    "Talarium - Panel principal"])


class TestVisual(NavegacionBase):
    def test_ajustes_escritorio(self):
        self.check(["", "3", "1", "7", "5", "7"],
                   ["Visual - apariencia", "Talarium - Panel principal"],
                   any_of=["Ajustes GNOME", "Ajustes KDE", "Ajustes XFCE",
                           "aún no tiene ajustes"])

    def test_fuentes_sudo_degradado(self):
        self.check(["", "3", "2", "5", "7"],
                   ["Permisos", "Talarium - Panel principal"])

    def test_zsh_sudo_degradado(self):
        self.check(["", "3", "3", "5", "7"],
                   ["Permisos", "Talarium - Panel principal"])

    def test_trim(self):
        self.check(["", "3", "4", "5", "7"],
                   ["Talarium - Panel principal"],
                   any_of=["Permisos", "TRIM", "No se detectó un disco SSD"])


class TestConsejos(NavegacionBase):
    def test_lista_y_cancela(self):
        self.check(["", "4", "", "7"],
                   ["Recomendaciones", "No seleccionaste ninguna recomendación.",
                    "Talarium - Panel principal"])


class TestBackup(NavegacionBase):
    def test_crear_copia(self):
        self.check(["", "5", "1", "4", "7"],
                   ["Creando copia de seguridad", "Talarium - Panel principal"])

    def test_listar_sin_copias(self):
        self.check(["", "5", "3", "4", "7"],
                   ["No hay copias de seguridad todavía",
                    "Talarium - Panel principal"])

    def test_restaurar_sin_copias(self):
        self.check(["", "5", "2", "4", "7"],
                   ["No hay copias de seguridad.",
                    "Talarium - Panel principal"])


class TestAyudaYSalida(NavegacionBase):
    def test_ayuda(self):
        self.check(["", "6", "7"], ["Ayuda", "Talarium v"])

    def test_salir_directo(self):
        rc, out = run_app(["", "7"])
        self.assertEqual(rc, 0)
        self.assertIn("Talarium - Panel principal", out)


class TestDialogSiDisponible(unittest.TestCase):
    @unittest.skipUnless(shutil.which("dialog"), "dialog no está instalado")
    def test_panel_principal_se_dibuja(self):
        import pty
        import time

        pid, fd = pty.fork()
        if pid == 0:
            os.execv(sys.executable, [sys.executable, "-m", "talarium"])
        out = b""
        try:
            for _ in range(40):  # hasta ~6 s
                import select
                r, _, _ = select.select([fd], [], [], 0.15)
                if r:
                    try:
                        data = os.read(fd, 65536)
                    except OSError:
                        break
                    if not data:
                        break
                    out += data
                time.sleep(0.02)
            os.write(fd, b"\x1b")  # Esc cancela el menú principal
            time.sleep(0.5)
            while True:
                import select
                r, _, _ = select.select([fd], [], [], 0.2)
                if not r:
                    break
                try:
                    data = os.read(fd, 65536)
                except OSError:
                    break
                if not data:
                    break
                out += data
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                os.kill(pid, 9)
                os.waitpid(pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass
        text = out.decode(errors="replace")
        self.assertIn("Talarium", text)


if __name__ == "__main__":
    unittest.main()
