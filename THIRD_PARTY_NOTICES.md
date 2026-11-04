# Licensing and provenance notices

The original Blind Pew implementation is offered under the [MIT license](LICENSE),
Copyright (c) 2026 Andrey Popovich. Retain that notice and the permission text
when redistributing it. This grant does not relicense third-party software,
grant trademark rights, or establish ownership of externally referenced data.

## Functional transliteration references

`data/profiles.json` contains 916 context/replacement rules across eight profiles,
plus reverse mappings and metadata. The supplied `tools/import_reference.py`
extracts mapping arrays from locally saved Translit.ru pages. The data records
reference dates and page hashes; see [docs/REFERENCE.md](docs/REFERENCE.md).
The executable JavaScript, HTML, branding and images of that site are not bundled.

The site's [terms](https://translit.ru/info/disclaimer/) describe personal,
noncommercial site use. Its [license page](https://translit.ru/info/licenses/)
identifies third-party website components, but does not supply an MIT grant for
the transliteration tables. No separate permission for these tables is recorded
in this repository. Compatibility data and a site's executable code are distinct;
this notice makes no determination about copyright/database protection of the
particular mappings, contractual scope or rights in a particular jurisdiction.
Translit.ru is a reference, not an endorsement or affiliation.

## External runtime components

These components are installed by the OS package manager and remain separate,
replaceable system packages. Blind Pew does not copy their source or libraries
into its DEB and imposes no restriction on modifying or debugging them.

| Component | Upstream terms | Integration / source |
|---|---|---|
| Python | PSF license and component notices | Interpreter; https://docs.python.org/3/license.html |
| PyGObject | LGPL-2.1-or-later | GI bindings; https://pygobject.gnome.org/ |
| GLib / GTK3 / GTK4 | LGPL-2.1-or-later | Shared libraries; https://docs.gtk.org/ |
| IBus | LGPL-2.1-or-later (with component notices) | Input framework and IPC; https://github.com/ibus/ibus |
| Ayatana AppIndicator | LGPL-3.0; see individual file notices | Shared indicator library; https://github.com/AyatanaIndicators/libayatana-appindicator |
| GNOME Shell | GPL-2.0-or-later | Shell hosting the separately supplied bridge; https://gitlab.gnome.org/GNOME/gnome-shell |
| im-config / Xfconf and desktop helpers | See each installed package's copyright file | Invoked as external commands, not embedded |

Exact notices for the installed versions are in `/usr/share/doc/<package>/copyright`.
The CI artifact includes `system-packages.tsv` to identify its test environment.
Copies of the LGPL/GPL texts are in [LICENSES](LICENSES); these texts do not
change the MIT terms of Blind Pew's original implementation.

The bridge's source and MIT notice are shipped together. MIT is GPL-compatible;
redistribution as part of a GNOME Shell combined work must also respect the
applicable GPL terms. Do not describe GNOME Shell as MIT-licensed. GNOME's
[extension licensing guidance](https://gjs.guide/extensions/review-guidelines/review-guidelines.html#licensing)
also permits inclusion of MIT code under GPL-compatible distribution terms.

## Artwork, interface text and screenshots

The project archive supplies `docs/blind-pew-logo.png` and `assets/blind-pew.svg`.
Project creation records describe an AI-assisted pirate-logo design requested
for Blind Pew. No stock-image source, licensed font file or third-party graphic
is embedded in the simple SVG. A supplied asset or generation record alone does
not establish worldwide trademark clearance or exclusive copyright protection.
The logo SHA-256 is recorded in [docs/LEGAL_REVIEW.md](docs/LEGAL_REVIEW.md).

The English screenshots were captured from the installed application in a real
GNOME 46 / Ubuntu 24.04 Wayland session. They include desktop UI and do not imply
endorsement by GNOME or Canonical. System fonts/icons are rendered in screenshots,
not redistributed as font or icon packages.

The interface language behavior and palette reference the author's Malferma Libro
project. Blind Pew does not import its Python modules or ship its translation
catalogs. Both projects use conventional locale aliases and language endonyms.
Malferma Libro's own GPL license remains unchanged.
