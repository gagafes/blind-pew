"""Idempotent session startup; called by the GUI in a worker thread."""
from dataclasses import dataclass
import os
import subprocess
import time
from .i18n import tr


@dataclass(frozen=True)
class Result:
    ready: bool
    needs_login: bool
    message: str  # Diagnostic details only; the GUI translates the status live.


def _run(args, timeout=4):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess(args, 1, '', str(error))


def _running():
    return _run(['ibus', 'list-engine'], timeout=2).returncode == 0


def _wait_ready():
    for _ in range(10):
        if _running():
            return True
        time.sleep(0.1)
    return False


def ensure_ibus():
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        return Result(False, False, tr('Open Blind Pew in your desktop session.'))
    if not os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
        return Result(False, False, tr('Open Blind Pew in your desktop session.'))
    gnome = 'gnome' in os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
    wayland = os.environ.get('XDG_SESSION_TYPE') == 'wayland' or bool(os.environ.get('WAYLAND_DISPLAY'))
    login = False
    notice = ''
    if not gnome:
        # im-config preserves files it does not own. Do not rewrite its choice
        # on every launch, and never force-remove a custom .xinputrc.
        state = _run(['im-config', '-m'])
        lines = state.stdout.splitlines()
        configured = state.returncode == 0 and len(lines) > 1 and lines[1] == 'ibus'
        if not configured:
            configured_result = _run(['im-config', '-n', 'ibus'])
            if configured_result.returncode:
                notice = tr('Settings unavailable') + ': ' + (
                    configured_result.stderr.strip() or configured_result.stdout.strip() or
                    tr('Settings unavailable'))[:240]
        login = (os.environ.get('GTK_IM_MODULE') != 'ibus' or
                 os.environ.get('XMODIFIERS') != '@im=ibus')
    if _running():
        ready = True
    else:
        ready = False
        if gnome:
            # GNOME owns its IBus session unit. Starting is safe for an active
            # service; restarting/replacing would disrupt another input method.
            result = _run(['ibus', 'start', '--type=systemd'], timeout=6)
            ready = _wait_ready() if result.returncode == 0 else _running()
        if not ready:
            command = ['ibus-daemon', '--daemonize']
            if gnome:
                command += ['--panel', 'disable']
            if not wayland:
                command += ['--xim']
            result = _run(command, timeout=6)
            ready = _wait_ready() if result.returncode == 0 else _running()
            if not ready:
                detail = (result.stderr.strip() or result.stdout.strip())[:240]
                return Result(False, login, ' '.join(part for part in (detail, notice) if part))
    return Result(ready, login, notice)
