"""Tests de la desinstalación de herramientas instaladas.

Ejecutar desde la raíz del proyecto:
    python3 -m unittest discover -s tests -v
"""

import unittest
from types import SimpleNamespace

from talarium.errors import CommandError, UserExit
from talarium.modules.common import (
    remove_packages,
    run_privileged,
    split_packages,
    operation_completed,
)
from talarium.modules.software import menu_uninstall


class FakeUI:
    def __init__(self, checklist=None, yesno=True, menu="menu"):
        self.alerts = []
        self.checklist_ret = checklist
        self.yesno_ret = yesno
        self.menu_ret = menu

    def alert(self, _title, msg):
        self.alerts.append(msg)

    def checklist(self, _t, _s, _items):
        return self.checklist_ret

    def yesno(self, _t, _s):
        return self.yesno_ret

    def menu(self, _t, _s, _items):
        return self.menu_ret


class FakeSudo:
    def ensure(self):
        return True


class FakePM:
    def __init__(self):
        self.install_calls = []
        self.remove_calls = []

    def install(self, pkgs):
        self.install_calls.append(list(pkgs))

    def remove(self, pkgs):
        self.remove_calls.append(list(pkgs))


class FakeFlatpak:
    def __init__(self):
        self.install_calls = []
        self.remove_calls = []

    def install(self, pkgs):
        self.install_calls.append(list(pkgs))

    def remove(self, pkgs):
        self.remove_calls.append(list(pkgs))


def make_ctx(ui=None):
    return SimpleNamespace(
        ui=ui or FakeUI(),
        sudo=FakeSudo(),
        pm=FakePM(),
        flatpak=FakeFlatpak(),
        distro=SimpleNamespace(aur_helper=""),
    )


class TestRunPrivileged(unittest.TestCase):
    def test_success_without_return_value_is_true(self):
        ctx = make_ctx()
        self.assertTrue(run_privileged(ctx, lambda: None))

    def test_success_with_return_value_is_preserved(self):
        ctx = make_ctx()
        self.assertEqual(run_privileged(ctx, lambda: 42), 42)

    def test_failure_returns_none_and_alerts(self):
        ctx = make_ctx()

        def fail():
            raise CommandError("boom", cmd="x", code=1)

        self.assertIsNone(run_privileged(ctx, fail))
        self.assertIn("boom", ctx.ui.alerts[0])


class TestRemovePackages(unittest.TestCase):
    def test_mixed_remove_calls_pm_and_flatpak(self):
        ctx = make_ctx()
        ok = remove_packages(ctx, ["git", "flatpak:org.foo"])
        self.assertTrue(ok)
        self.assertEqual(ctx.pm.remove_calls, [["git"]])
        self.assertEqual(ctx.flatpak.remove_calls, [["org.foo"]])

    def test_remove_failure_is_false(self):
        ctx = make_ctx()

        def boom(_pkgs):
            raise CommandError("dnf falló", cmd="dnf remove", code=1)

        ctx.pm.remove = boom
        self.assertFalse(remove_packages(ctx, ["git"]))


class TestSplitPackages(unittest.TestCase):
    def test_split(self):
        native, aur, flat = split_packages(["git", "aur:foo", "flatpak:org.bar"])
        self.assertEqual(native, ["git"])
        self.assertEqual(aur, ["foo"])
        self.assertEqual(flat, ["org.bar"])


class TestOperationCompleted(unittest.TestCase):
    def test_menu_returns_to_menu(self):
        ctx = make_ctx(ui=FakeUI(menu="menu"))
        operation_completed(ctx)  # no debe lanzar

    def test_exit_raises_userexit(self):
        ctx = make_ctx(ui=FakeUI(menu="exit"))
        with self.assertRaises(UserExit):
            operation_completed(ctx)


class TestMenuUninstall(unittest.TestCase):
    def test_uninstall_end_to_end(self):
        pm = FakePM()

        class Catalog:
            def software(self, _pm):
                return {"esenciales": ["git", "vim"], "extra": ["htop"]}

            def github(self):
                return []

        class PM:
            def is_installed(self, p):
                return p in ("git", "htop")

            def remove(self, pkgs):
                pm.remove_calls.append(list(pkgs))

        ctx = SimpleNamespace(
            ui=FakeUI(checklist=["git", "htop"], yesno=True, menu="exit"),
            sudo=FakeSudo(),
            catalog=Catalog(),
            pm=PM(),
            flatpak=FakeFlatpak(),
            distro=SimpleNamespace(pm="dnf", aur_helper=""),
        )
        with self.assertRaises(UserExit):
            menu_uninstall(ctx)
        self.assertEqual(pm.remove_calls, [["git", "htop"]])

    def test_no_installed_shows_alert(self):
        class Catalog:
            def software(self, _pm):
                return {"esenciales": ["git"]}

            def github(self):
                return []

        class PM:
            def is_installed(self, _p):
                return False

        ui = FakeUI()
        ctx = SimpleNamespace(
            ui=ui,
            sudo=FakeSudo(),
            catalog=Catalog(),
            pm=PM(),
            flatpak=FakeFlatpak(),
            distro=SimpleNamespace(pm="dnf", aur_helper=""),
        )
        menu_uninstall(ctx)
        self.assertTrue(ui.alerts)
        self.assertIn("No hay herramientas instaladas", ui.alerts[0])


if __name__ == "__main__":
    unittest.main()
