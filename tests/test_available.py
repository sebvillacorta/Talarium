"""Tests de disponibilidad de paquetes en los repos por distro (PM reales).

Usa un Runner simulado que devuelve respuestas fijas por comando, de modo
que se comprueba la lógica de cada gestor (dnf, pacman, apt, zypper, xbps,
apk) sin tocar el sistema real.

Ejecutar desde la raíz del proyecto:
    python3 -m unittest discover -s tests -v
"""

import subprocess
import unittest
from types import SimpleNamespace

from talarium.core.packagemanager import factory
from talarium.modules import software as software_mod


class FakeRunner:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def run(self, argv, capture=False, timeout=None, check=False):
        self.calls.append(tuple(argv))
        rc, out, err = self.responses.get(tuple(argv), (0, "", ""))
        proc = subprocess.CompletedProcess(list(argv), rc, stdout=out, stderr=err)
        if check and rc != 0:
            from talarium.errors import CommandError
            raise CommandError(f"falló {argv}", cmd=" ".join(argv), code=rc)
        return proc


def pm_for(pm_name, responses):
    return factory(FakeRunner(responses), pm_name)


class TestDnfDisponibilidad(unittest.TestCase):
    def test_batch_con_mezcla_disponible_no(self):
        pm = pm_for("dnf", {
            ("dnf", "repoquery", "--quiet", "git", "curl", "fantasma"):
                (0, "git-0:2.53.0-1.fc44.x86_64\ncurl-0:8.0.1-1.fc44.x86_64\n", ""),
        })
        res = pm.available_batch(["git", "curl", "fantasma"])
        self.assertEqual(res, {"git": True, "curl": True, "fantasma": False})

    def test_batch_sin_metadatos_devuelve_desconocido(self):
        pm = pm_for("dnf", {
            ("dnf", "repoquery", "--quiet", "git"): (1, "", "Error: no metadata"),
        })
        self.assertIsNone(pm.available_batch(["git"])["git"])

    def test_batch_usa_caché(self):
        pm = pm_for("dnf", {
            ("dnf", "repoquery", "--quiet", "git"): (0, "git-0:2.53.0-1.fc44.x86_64\n", ""),
        })
        first = pm.available_batch(["git"])
        second = pm.available_batch(["git"])
        self.assertEqual(first, {"git": True})
        self.assertEqual(second, {"git": True})
        repo = ("dnf", "repoquery", "--quiet", "git")
        self.assertEqual(pm.r.calls.count(repo), 1)


class TestOtrosGestoresDisponibilidad(unittest.TestCase):
    def _one(self, pm_name, argv, rc, out, err=""):
        pm = pm_for(pm_name, {tuple(argv): (rc, out, err)})
        return pm.available(argv[-1])

    def test_pacman(self):
        self.assertTrue(self._one("pacman", ["pacman", "-Si", "git"], 0,
                                  "Repository: core\nName: git\n", ""))
        self.assertFalse(self._one("pacman", ["pacman", "-Si", "nope"], 1, "",
                                   "error: package 'nope' was not found"))
        self.assertIsNone(self._one("pacman", ["pacman", "-Si", "git"], 1, "",
                                    "error: database file for 'core' does not exist"))

    def test_apt(self):
        self.assertTrue(self._one("apt", ["apt-cache", "show", "git"], 0,
                                  "Package: git\n"))
        self.assertFalse(self._one("apt", ["apt-cache", "show", "nope"], 100, ""))
        self.assertIsNone(self._one("apt", ["apt-cache", "show", "git"], 1, ""))

    def test_zypper(self):
        self.assertTrue(self._one("zypper", ["zypper", "se", "-x", "--no-headings", "git"], 0,
                                  "git | package | 2.39.0 | repo |  |  |\n"))
        self.assertFalse(self._one("zypper", ["zypper", "se", "-x", "--no-headings", "nope"], 0, ""))
        self.assertIsNone(self._one("zypper", ["zypper", "se", "-x", "--no-headings", "git"], 104, ""))

    def test_xbps(self):
        self.assertTrue(self._one("xbps", ["xbps-query", "-Rs", "git"], 0,
                                  "* git-2.39.0_1 (main)\n"))
        self.assertFalse(self._one("xbps", ["xbps-query", "-Rs", "nope"], 1, ""))
        self.assertIsNone(self._one("xbps", ["xbps-query", "-Rs", "git"], 2, ""))

    def test_apk(self):
        self.assertTrue(self._one("apk", ["apk", "search", "-e", "git"], 0,
                                  "git-2.39.2-r0\n"))
        self.assertFalse(self._one("apk", ["apk", "search", "-e", "nope"], 1, ""))
        self.assertIsNone(self._one("apk", ["apk", "search", "-e", "git"], 2, ""))


class TestShowCategoryFiltraNoDisponibles(unittest.TestCase):
    class FakeUI:
        def __init__(self, yesnos):
            self.yesnos = list(yesnos)
            self.checklist_items = None

        def checklist(self, _t, _s, items):
            self.checklist_items = list(items)
            return ["git", "imposible", "flatpak:com.fantasma"]

        def yesno(self, _t, _s):
            return self.yesnos.pop(0)

        def menu(self, _t, _s, _items):
            return "install"

        def alert(self, _t, _s):
            pass

    def _ctx(self, yesnos, flatpak_avail=False):
        ui = self.FakeUI(yesnos)
        catalog = SimpleNamespace(
            software=lambda pm: {"esenciales": ["git", "imposible", "flatpak:com.fantasma"]},
            descriptions=lambda: {},
        )

        class PM:
            def is_installed(self, p):
                return False

            def available(self, p):
                return {"git": True, "imposible": False}[p]

            def name(self):
                return "apt"

        ctx = SimpleNamespace(ui=ui, catalog=catalog, pm=PM(),
                              distro=SimpleNamespace(pm="apt", name="Ubuntu"),
                              flatpak=SimpleNamespace(available=flatpak_avail))
        return ctx, ui

    def test_marca_no_disponible_en_checklist(self):
        ctx, ui = self._ctx([True, True])
        software_mod.show_category(ctx, "esenciales")
        labels = {tag: label for tag, label, _ in ui.checklist_items}
        self.assertIn("NO DISPONIBLE", labels["imposible"])
        self.assertIn("NO DISPONIBLE", labels["flatpak:com.fantasma"])
        self.assertNotIn("NO DISPONIBLE", labels["git"])

    def test_instala_solo_los_disponibles(self):
        ctx, ui = self._ctx([True, True])
        installed = []
        software_mod.install_packages = lambda c, pkgs: (installed.append(list(pkgs)) or True)
        software_mod.show_category(ctx, "esenciales")
        self.assertEqual(installed, [["git"]])

    def test_aborta_si_no_acepta_el_aviso(self):
        ctx, ui = self._ctx([False, False])
        installed = []
        software_mod.install_packages = lambda c, pkgs: (installed.append(list(pkgs)) or True)
        software_mod.show_category(ctx, "esenciales")
        self.assertEqual(installed, [])


if __name__ == "__main__":
    unittest.main()
