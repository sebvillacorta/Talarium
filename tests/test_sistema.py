"""Test general del sistema: verifica Talarium de punta a punta.

Cubre el arranque real, el CLI, la integridad de toda la configuración,
el import de todos los módulos, la fábrica de interfaces, las funciones
de detección del sistema y los scripts bash del instalador.

Ejecutar desde la raíz del proyecto:
    python3 -m unittest discover -s tests -v
"""

import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path

from talarium import __version__
from talarium.config import CONFIG_DIR, THEME_FILE
from talarium.core.catalog import Catalog
from talarium.core.system import (
    cores,
    detect_de,
    detect_distro,
    gpu_vendor,
    has_command,
    is_systemd,
    is_ssd,
    mem_gb,
)
from talarium.ui import create_ui

ROOT = Path(__file__).resolve().parent.parent
SUPPORTED_PM = ("dnf", "pacman", "apt", "zypper", "xbps", "apk")


class TestCLI(unittest.TestCase):
    def _run(self, *args, input_str=""):
        return subprocess.run([sys.executable, "-m", "talarium"] + list(args),
                              input=input_str, capture_output=True, text=True,
                              timeout=60)

    def test_version(self):
        r = self._run("--version")
        self.assertEqual(r.returncode, 0)
        self.assertIn("talarium", r.stdout)
        self.assertIn(__version__, r.stdout)

    def test_doctor(self):
        r = self._run("--doctor")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Talarium - Diagnóstico", r.stdout)
        self.assertIn("Gestor de paq.", r.stdout)

    def test_arranque_y_salida_limpia(self):
        r = self._run(input_str="\n7\n")
        self.assertEqual(r.returncode, 0)

    def test_bash_syntax_de_scripts(self):
        for script in ("install.sh", "bin/talarium"):
            r = subprocess.run(["bash", "-n", str(ROOT / script)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"sintaxis incorrecta en {script}")


class TestConfiguracionIntegra(unittest.TestCase):
    def setUp(self):
        self.cat = Catalog()

    def test_catalogos_software_para_cada_gestor(self):
        for pm in SUPPORTED_PM:
            cats = self.cat.software(pm)
            self.assertTrue(cats, f"sin catálogo para {pm}")
            for cat, pkgs in cats.items():
                self.assertTrue(cat.strip(), f"{pm}: categoría vacía")
                self.assertTrue(pkgs, f"{pm}/{cat}: sin paquetes")
                self.assertTrue(all(p.strip() for p in pkgs),
                                f"{pm}/{cat}: paquete vacío")
                self.assertEqual(len(pkgs), len(set(pkgs)),
                                 f"{pm}/{cat}: paquete duplicado")

    def test_github_conf_bien_formado(self):
        for name, pattern, url, dest in self.cat.github():
            self.assertTrue(name and pattern and url and dest,
                            f"entrada inválida en github.conf: {name}")

    def test_descriptions_se_leen(self):
        self.assertIsInstance(self.cat.descriptions(), dict)

    def test_debloat_no_falla_para_escritorios_y_distros(self):
        for de in ("gnome", "kde", "xfce", "cinnamon", "mate"):
            for distro in ("fedora", "ubuntu", "arch"):
                self.assertIsInstance(self.cat.debloat(de, distro), list)

    def test_theme_existe(self):
        self.assertTrue(THEME_FILE.is_file(), f"falta el tema: {THEME_FILE}")

    def test_directorios_de_config_existen(self):
        self.assertTrue((CONFIG_DIR / "software").is_dir())
        self.assertTrue((CONFIG_DIR / "debloat").is_dir())


class TestModulosImportables(unittest.TestCase):
    def test_todos_los_modulos_importan(self):
        modulos = [
            "talarium.app", "talarium.cli", "talarium.context", "talarium.config",
            "talarium.errors", "talarium.sudo",
            "talarium.ui.base", "talarium.ui.dialog", "talarium.ui.text",
            "talarium.ui.banner",
            "talarium.core.system", "talarium.core.runner", "talarium.core.catalog",
            "talarium.core.packagemanager", "talarium.core.github",
            "talarium.modules.common", "talarium.modules.software",
            "talarium.modules.maintenance", "talarium.modules.visual",
            "talarium.modules.recommend", "talarium.modules.backup",
        ]
        for m in modulos:
            with self.subTest(m=m):
                __import__(m)

    def test_version_tiene_formato_valido(self):
        parts = __version__.split(".")
        self.assertGreaterEqual(len(parts), 2)
        self.assertTrue(all(p.isdigit() for p in parts))


class TestInterfaces(unittest.TestCase):
    def test_factory_texto(self):
        ui = create_ui(force="texto")
        self.assertEqual(ui.name, "texto")

    def test_factory_default_no_falla(self):
        ui = create_ui()
        self.assertIn(ui.name, ("dialog", "whiptail", "texto"))

    def test_texto_sin_entrada_sale_limpiamente(self):
        ui = create_ui(force="texto")
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                ui.menu("T", "S", [("a", "Opción A"), ("b", "Opción B")])
        self.assertEqual(cm.exception.code, 0)


class TestDeteccionDelSistema(unittest.TestCase):
    def test_detecta_distro_soportada(self):
        d = detect_distro()
        self.assertIn(d.pm, SUPPORTED_PM, f"gestor no soportado: {d.pm}")
        self.assertTrue(d.pm_bin)

    def test_funciones_de_hardware_no_fallan(self):
        self.assertGreaterEqual(mem_gb(), 0)
        self.assertGreater(cores(), 0)
        self.assertIn(gpu_vendor(), ("nvidia", "amd", "intel", "desconocida"))
        self.assertIsInstance(is_ssd(), bool)
        self.assertIsInstance(is_systemd(), bool)
        self.assertIsInstance(detect_de(), tuple)
        self.assertIsInstance(has_command("sh"), bool)


class TestArranqueCompleto(unittest.TestCase):
    def test_bootstrap_en_sistema_real(self):
        from talarium.app import TalariumApp
        the_app = TalariumApp(ui_force="texto")
        the_app.bootstrap()
        self.assertIsNotNone(the_app.ctx)
        self.assertIn(the_app.ctx.distro.pm, SUPPORTED_PM)
        self.assertEqual(the_app.ctx.pm.name, the_app.ctx.distro.pm)

    def test_doctor_funciona_inprocess(self):
        from talarium.app import run_doctor
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = run_doctor()
        self.assertEqual(rc, 0)
        self.assertIn("Talarium - Diagnóstico", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
