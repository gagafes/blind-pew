#!/bin/sh
set -eu
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT
cat > "$test_root/bus.conf" <<EOF
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN" "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <listen>unix:tmpdir=$test_root</listen>
  <auth>EXTERNAL</auth>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/><allow own="*"/>
  </policy>
</busconfig>
EOF
export PYTHONPATH=.
export XDG_CONFIG_HOME="$test_root/config"
export XDG_CACHE_HOME="$test_root/cache"
GSETTINGS_BACKEND=memory /usr/bin/python3 tests/settings_smoke.py
dbus-run-session --config-file="$test_root/bus.conf" -- /usr/bin/python3 tests/protocol_smoke.py
