# Security

Report security issues privately to **Andrey Popovich <gagafes@gmail.com>**.
Include the Blind Pew package version, OS/desktop version, reproduction steps
and expected impact. Do not include passwords, personal text or access tokens.
Use public GitHub issues for ordinary bugs, not undisclosed vulnerabilities.
The latest release is the supported version; fixes are not backported to older
packages.

Blind Pew runs as the desktop user. It has no network client, telemetry,
clipboard reader, device hook or keystroke log. It converts text delivered by
IBus and retains only the short suffix needed for composition. Password, PIN
and Private input purposes bypass conversion when the client marks them.
Applications that omit these hints cannot be identified as sensitive by the
engine. The text deliberately entered in the settings preview remains in that
window until it is cleared or closed.

Preferences and saved shortcut values live under the user's XDG configuration
directory. They contain settings and pre-existing shortcut commands, not typed
text. Settings are bounded, validated and replaced atomically with mode 0600.
The GNOME bridge uses the user's session bus and can only activate an existing
input source; it does not evaluate code or inject arbitrary commands.
Another program running as the same user is outside this isolation boundary.

Dependencies come from Debian/Ubuntu APT repositories; none are vendored or
installed through pip. Keep the OS updated to receive GTK, IBus, GLib and Python
security fixes. GitHub Actions use pinned action commits, read-only repository
permissions and checkout without persisted credentials.

CI checks source with Bandit and Pyflakes, scans Git history with Gitleaks and
runs input/privacy, preference and installed-package regressions. These checks
reduce risk; they are not a guarantee that every vulnerability is detectable.
