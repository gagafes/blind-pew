# Changelog

## 0.1.0-2 — 2026-11-04

Release preparation for the first public version. The application version
remains 0.1.0; the Debian revision advances so existing 0.1.0-1 installations
can upgrade normally.

- Bound preference reads; reject special files, symbolic links, deeply nested
  JSON and malformed shortcut backups without breaking startup.
- Persist original desktop settings before replacing them, so interrupted
  activation retains recovery information. Preserve independent user changes.
- Handle empty Xfce shortcut profiles and missing GNOME shortcut schemas.
- Require the Xfconf client library even when APT recommendations are disabled.
- Leave GTK's shared IBus connection intact when stopping the input monitor.
- Avoid duplicate IBus initialization and unbounded resource allocation on Ubuntu 24.04.
- Publish generated tray icons atomically without following cache symlinks.
- Convert large CLI input in bounded chunks, including text without newlines.
- Include screenshots and release/security documentation in the DEB.
- Use portable gzip metadata and a changelog-derived build timestamp/version.
- Test Ubuntu 24.04 and Debian 13, installed IBus engines, package lifecycle,
  source safety and desktop integration in CI.
- Keep English GNOME screenshots in all five READMEs.

## 0.1.0-1 — 2026-10-28

Initial package: eight transliteration profiles for seven languages, QWERTY
and QWERTZ, F12 and tray-wheel switching, GNOME/XFCE integration, 49 interface
catalogs and offline CLI conversion.
