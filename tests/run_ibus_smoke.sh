#!/bin/sh
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
set -eu
# Use an isolated test user profile; never touch a logged-in user's settings.
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT
mkdir -p "$test_root/config" "$test_root/cache" "$test_root/runtime"
chmod 700 "$test_root/runtime"
export XDG_CONFIG_HOME="$test_root/config"
export XDG_CACHE_HOME="$test_root/cache"
export XDG_RUNTIME_DIR="$test_root/runtime"
unset IBUS_ADDRESS
exec_body='ibus-daemon --replace --xim --panel disable --config disable --cache refresh --daemonize
/usr/bin/python3 tests/ibus_smoke.py'
dbus-run-session -- xvfb-run -a sh -ec "$exec_body"
