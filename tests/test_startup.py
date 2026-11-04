import os
import subprocess
import unittest
from unittest.mock import patch
from blind_pew import startup


class Startup(unittest.TestCase):
    def setUp(self):
        self.env = {'DISPLAY': ':1', 'DBUS_SESSION_BUS_ADDRESS': 'test-session',
                    'XDG_CURRENT_DESKTOP': 'GNOME', 'XDG_SESSION_TYPE': 'x11'}
        self.calls = []
        self.running = False
        self.systemd_ok = True
        self.direct_ok = True
        self.configured = True
        self.config_ok = True

    def execute(self, args, timeout=4):
        self.calls.append(args)
        code, out, err = 0, '', ''
        if args == ['ibus', 'list-engine']:
            code = 0 if self.running else 1
        elif args == ['im-config', '-m']:
            out = 'default\n' + ('ibus' if self.configured else 'custom') + '\nibus\n'
        elif args == ['im-config', '-n', 'ibus']:
            code = 0 if self.config_ok else 1
            err = '' if self.config_ok else 'Custom configuration preserved'
        elif args[:2] == ['ibus', 'start']:
            code = 0 if self.systemd_ok else 1
            self.running = self.systemd_ok
        elif args[0] == 'ibus-daemon':
            code = 0 if self.direct_ok else 1
            self.running = self.direct_ok
            err = '' if self.direct_ok else 'No display'
        else:
            raise AssertionError(args)
        return subprocess.CompletedProcess(args, code, out, err)

    def run_startup(self):
        with patch.dict(os.environ, self.env, clear=True), patch.object(startup, '_run', self.execute), patch.object(startup.time, 'sleep'):
            return startup.ensure_ibus()

    def test_existing_daemon_is_never_restarted(self):
        self.running = True
        result = self.run_startup()
        self.assertTrue(result.ready)
        self.assertEqual(self.calls, [['ibus', 'list-engine']])

    def test_gnome_prefers_systemd(self):
        self.assertTrue(self.run_startup().ready)
        self.assertIn(['ibus', 'start', '--type=systemd'], self.calls)
        self.assertFalse(any(c[0] in ('ibus-daemon', 'im-config') for c in self.calls))

    def test_gnome_wayland_fallback_has_no_xim_or_replace(self):
        self.systemd_ok = False
        self.env.update(XDG_SESSION_TYPE='wayland', WAYLAND_DISPLAY='wayland-0')
        self.assertTrue(self.run_startup().ready)
        self.assertIn(['ibus-daemon', '--daemonize', '--panel', 'disable'], self.calls)
        self.assertFalse(any('--replace' in c for c in self.calls))

    def test_xfce_configures_and_starts(self):
        self.env['XDG_CURRENT_DESKTOP'] = 'XFCE'
        self.configured = False
        result = self.run_startup()
        self.assertTrue(result.ready)
        self.assertTrue(result.needs_login)
        self.assertIn(['im-config', '-n', 'ibus'], self.calls)
        self.assertIn(['ibus-daemon', '--daemonize', '--xim'], self.calls)

    def test_xfce_preconfigured_is_idempotent(self):
        self.env.update(XDG_CURRENT_DESKTOP='XFCE', GTK_IM_MODULE='ibus', XMODIFIERS='@im=ibus')
        self.running = True
        result = self.run_startup()
        self.assertTrue(result.ready)
        self.assertFalse(result.needs_login)
        self.assertNotIn(['im-config', '-n', 'ibus'], self.calls)
        self.assertFalse(any(c[0] == 'ibus-daemon' for c in self.calls))

    def test_custom_config_not_forced(self):
        self.env['XDG_CURRENT_DESKTOP'] = 'XFCE'
        self.configured = False
        self.config_ok = False
        result = self.run_startup()
        self.assertIn('Custom configuration preserved', result.message)
        self.assertFalse(any('REMOVE' in c for c in self.calls))

    def test_start_failure_is_reported(self):
        self.systemd_ok = self.direct_ok = False
        result = self.run_startup()
        self.assertFalse(result.ready)
        self.assertIn('No display', result.message)

    def test_no_desktop_does_not_change_settings(self):
        del self.env['DISPLAY']
        self.assertFalse(self.run_startup().ready)
        self.assertEqual(self.calls, [])

    def test_no_session_bus_does_not_change_settings(self):
        del self.env['DBUS_SESSION_BUS_ADDRESS']
        self.assertFalse(self.run_startup().ready)
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
