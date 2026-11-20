# Changelog

## 0.2.0-1

- Add offline Arabic phonetic input on QWERTY and QWERTZ. The profile supports
  explicit hamza, diacritics and dot-prefixed keys while preserving ordinary
  numbers. Settings include an RTL preview and the input table.
- Use the desktop keyboard icon in place of the old application artwork.
- Restore the previous IBus input method when toggling transliteration off.
- Preserve edited F12 bindings when retrying startup, and validate the saved
  desktop settings before changing them.
- Show input source activation errors and use the fallback tray icon if a
  country indicator cannot be stored.
- Handle a closed output pipe without a Python traceback.
- Verify the release version and assets against the selected build in CI.

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
