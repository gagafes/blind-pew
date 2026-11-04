#!/usr/bin/python3
"""Isolated test display with an authenticated local D-Bus session."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

with tempfile.TemporaryDirectory(prefix='translit-gui-test-') as tmp:
    root = Path(tmp)
    config = root / 'bus.conf'
    config.write_text(f'''<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN" "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig><type>session</type><standard_session_servicedirs/><listen>unix:tmpdir={root}</listen>
<auth>EXTERNAL</auth><policy context="default"><allow send_destination="*" eavesdrop="true"/><allow eavesdrop="true"/><allow own="*"/></policy></busconfig>''')
    for display in range(300, 400):
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', 6000 + display))
                break
            except OSError:
                continue
    else:
        raise RuntimeError('No free test display')
    env = dict(os.environ, DISPLAY=f'127.0.0.1:{display}', XDG_SESSION_TYPE='x11',
               XDG_CURRENT_DESKTOP='XFCE', XDG_CONFIG_HOME=str(root/'config'),
               XDG_CACHE_HOME=str(root/'cache'), GSETTINGS_BACKEND='memory',
               NO_AT_BRIDGE='1', GTK_A11Y='none', GSK_RENDERER='cairo', PYTHONPATH='.')
    env.pop('WAYLAND_DISPLAY', None)
    server = subprocess.Popen(['Xvfb', f':{display}', '-nolisten', 'unix', '-nolisten', 'local',
                               '-listen', 'tcp', '-ac', '-screen', '0', '1100x850x24'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for _ in range(60):
            try:
                with socket.create_connection(('127.0.0.1', 6000 + display), 0.1):
                    break
            except OSError:
                time.sleep(0.05)
        subprocess.run(['dbus-run-session', '--config-file='+str(config), '--',
                        '/usr/bin/python3', sys.argv[1] if len(sys.argv) > 1 else
                        'tests/gui_smoke.py'], env=env, check=True, timeout=35)
    finally:
        server.terminate()
        try:
            server.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            server.kill()
            server.communicate()
