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
export IBUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/ibus"
cat > "$test_root/run.sh" <<'INNER'
#!/bin/sh
set -eu
gsettings set org.freedesktop.ibus.general use-global-engine true
ibus-daemon --address="$IBUS_ADDRESS" --panel disable --cache refresh &
ibus_pid=$!
trap 'kill "$ibus_pid" 2>/dev/null || true; wait "$ibus_pid" 2>/dev/null || true' EXIT
for attempt in $(seq 1 40); do
    kill -0 "$ibus_pid"
    if ibus list-engine >/dev/null 2>&1; then break; fi
    sleep 0.25
done
/usr/bin/python3 tests/ibus_smoke.py
INNER
dbus-run-session -- xvfb-run -a -s '-screen 0 1100x850x24 -nolisten tcp' sh "$test_root/run.sh"
