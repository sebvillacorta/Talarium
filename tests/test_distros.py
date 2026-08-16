"""Compatibilidad de Talarium con las distros más populares.

Verifica que la detección, la fábrica de gestores y los catálogos de
software funcionan para Arch, Ubuntu/Debian/Mint, Fedora/RHEL, openSUSE,
Void y Alpine.

Ejecutar desde la raíz del proyecto:
    python3 -m unittest discover -s tests -v
"""

import unittest
from unittest import mock

from talarium import app as app_module
from talarium.core.catalog import Catalog
from talarium.core.packagemanager import factory
from talarium.core.runner import Runner
from talarium.core.system import (
    DistroInfo,
    _match_pm,
    _pm_binary,
    detect_distro,
    require_supported,
)
from talarium.errors import UnsupportedDistro

# (id, nombre, gestor esperado, binario esperado)
POPULAR = [
    # Arch y derivados
    ("arch", "Arch Linux", "pacman", "pacman"),
    ("manjaro", "Manjaro", "pacman", "pacman"),
    ("endeavouros", "EndeavourOS", "pacman", "pacman"),
    ("garuda", "Garuda Linux", "pacman", "pacman"),
    ("cachyos", "CachyOS", "pacman", "pacman"),
    # Debian / Ubuntu / Mint y derivados
    ("debian", "Debian GNU/Linux", "apt", "apt-get"),
    ("ubuntu", "Ubuntu", "apt", "apt-get"),
    ("linuxmint", "Linux Mint", "apt", "apt-get"),
    ("pop", "Pop!_OS", "apt", "apt-get"),
    ("elementary", "elementary OS", "apt", "apt-get"),
    ("zorin", "Zorin OS", "apt", "apt-get"),
    ("mx", "MX Linux", "apt", "apt-get"),
    ("kali", "Kali GNU/Linux", "apt", "apt-get"),
    # RedHat / Fedora y derivados
    ("fedora", "Fedora Linux", "dnf", "dnf"),
    ("rhel", "Red Hat Enterprise Linux", "dnf", "dnf"),
    ("centos", "CentOS Stream", "dnf", "dnf"),
    ("rocky", "Rocky Linux", "dnf", "dnf"),
    ("almalinux", "AlmaLinux", "dnf", "dnf"),
    ("nobara", "Nobara Linux", "dnf", "dnf"),
    # SUSE
    ("opensuse-tumbleweed", "openSUSE Tumbleweed", "zypper", "zypper"),
    ("opensuse-leap", "openSUSE Leap", "zypper", "zypper"),
    ("opensuse", "openSUSE", "zypper", "zypper"),
    # Otros
    ("void", "Void Linux", "xbps", "xbps-install"),
    ("alpine", "Alpine Linux", "apk", "apk"),
]

UNSUPPORTED = [
    ("gentoo", "Gentoo"),
    ("slackware", "Slackware"),
    ("nixos", "NixOS"),
    ("unknown", "Sistema desconocido"),
]


class TestDeteccionDistro(unittest.TestCase):
    def test_mapping_a_gestor_correcto(self):
        for distro_id, name, pm, pm_bin in POPULAR:
            self.assertEqual(_match_pm(distro_id), pm, f"{name} -> {pm}")
            self.assertEqual(_pm_binary(pm), pm_bin, f"{name} -> binario")

    def test_detect_distro_completo(self):
        for distro_id, name, pm, pm_bin in POPULAR:
            with mock.patch("talarium.core.system._read_os_release",
                            return_value={"ID": distro_id, "NAME": name,
                                          "VERSION_ID": "1"}):
                d = detect_distro()
                self.assertEqual(d.pm, pm, f"{name} (pm)")
                self.assertEqual(d.pm_bin, pm_bin, f"{name} (binario)")

    def test_distro_no_soportada_lanza(self):
        for distro_id, name in UNSUPPORTED:
            d = DistroInfo(id=distro_id, name=name)
            with self.assertRaises(UnsupportedDistro, msg=name):
                require_supported(d)


class TestGestorDePaquetes(unittest.TestCase):
    def test_factory_crea_gestor_para_cada_distro(self):
        runner = Runner(object())
        for distro_id, name, pm, _ in POPULAR:
            try:
                mgr = factory(runner, pm)
            except Exception as exc:  # noqa: BLE001 - mensaje de fallo claro
                self.fail(f"{name}: no se pudo crear el gestor '{pm}': {exc}")
            self.assertEqual(mgr.name, pm)
            self.assertTrue(mgr.install_cmd, f"{name}: sin comando de instalación")
            self.assertTrue(mgr.remove_cmd, f"{name}: sin comando de eliminación")
            self.assertTrue(mgr.query_cmd, f"{name}: sin comando de consulta")


class TestCatalogoSoftware(unittest.TestCase):
    def test_catalogo_existe_para_cada_gestor(self):
        catalog = Catalog()
        for distro_id, name, pm, _ in POPULAR:
            try:
                cats = catalog.software(pm)
            except Exception as exc:  # noqa: BLE001
                self.fail(f"{name}: el catálogo de {pm} no se puede leer: {exc}")
            self.assertTrue(cats, f"{name}: catálogo de {pm} vacío o inexistente")


class TestBootstrapEnCadaDistro(unittest.TestCase):
    def test_arranque_completo_para_cada_distro(self):
        for distro_id, name, pm, pm_bin in POPULAR:
            d = DistroInfo(id=distro_id, name=name, version="1", pm=pm,
                           pm_bin=pm_bin, has_sudo=True)
            with mock.patch.object(app_module, "detect_distro", return_value=d):
                the_app = app_module.TalariumApp(ui_force="texto")
                try:
                    the_app.bootstrap()
                except Exception as exc:  # noqa: BLE001
                    self.fail(f"{name}: el arranque falló: {exc}")
                self.assertIsNotNone(the_app.ctx, f"{name}: sin contexto")
                self.assertEqual(the_app.ctx.pm.name, pm)


if __name__ == "__main__":
    unittest.main()
