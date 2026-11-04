#!/usr/bin/python3
"""Run GUI checks on an authenticated local display and private session bus."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile


with tempfile.TemporaryDirectory(prefix='blind-pew-gui-test-') as tmp:
    root = Path(tmp)
    runtime = root / 'runtime'
    runtime.mkdir(mode=0o700)
    env = dict(os.environ, XDG_SESSION_TYPE='x11', XDG_CURRENT_DESKTOP='XFCE',
               XDG_CONFIG_HOME=str(root / 'config'), XDG_CACHE_HOME=str(root / 'cache'),
               XDG_RUNTIME_DIR=str(runtime), GSETTINGS_BACKEND='memory',
               NO_AT_BRIDGE='1', GTK_A11Y='none', GSK_RENDERER='cairo', PYTHONPATH='.')
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'IBUS_ADDRESS', 'DBUS_SESSION_BUS_ADDRESS'):
        env.pop(key, None)
    subprocess.run(['dbus-run-session', '--', 'xvfb-run', '-a', '-s',
                    '-screen 0 1100x850x24 -nolisten tcp', '/usr/bin/python3',
                    sys.argv[1] if len(sys.argv) > 1 else 'tests/gui_smoke.py'],
                   env=env, check=True, timeout=45)
