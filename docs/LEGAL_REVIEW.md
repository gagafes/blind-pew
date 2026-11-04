# Provenance and license review — 2026-11-04

## Scope and conclusion

This is a source/provenance review, not a legal opinion, universal originality
certificate, patent search or worldwide trademark clearance. MIT is retained for
the original implementation. The maintainer has directed release preparation to
continue after review of the Translit.ru data provenance described below.
No permission or legal clearance is inferred from that decision.

Reviewed: the complete imported repository, executable Python/GJS, tests,
packaging, 49 interface catalogs, eight data profiles, artwork, screenshots,
license files, supplied source archives and the external runtime interfaces.
The source archives do not contain the full pre-import development history.

## Findings

| Item | Evidence / result | Qualification |
|---|---|---|
| Original Python/GJS | Manual source review found no bundled third-party implementation, obfuscated payload or imported website script | Public search cannot establish exclusive authorship or absence of every possible match |
| Malferma Libro comparison | No identical blob/file in the imported Blind Pew tree and Malferma Libro tree `e39fc9c7fc2b98942bfef48afc9ebf9f945a41a7`; locale-module comparison found a longest exact Python token run of 13 before quote normalization | Short common idioms and shared locale behavior are not evidence of wholly unique code; this is a limited comparison, not a plagiarism percentage |
| Translit.ru data | Importer extracts functional mapping arrays; the current JSON contains 916 ordered context/replacement entries across eight profiles and reverse maps | No redistribution grant for these tables was located in the site's terms/license page or supplied archives; protection and contractual scope were not legally adjudicated |
| MIT notice | Full license and copyright retained; installed documentation and GNOME extension include the notice | The MIT grant can cover only rights the licensor has |
| Runtime dependencies | System packages are dynamically used or invoked through IPC/commands; source and binaries are not vendored | Follow their own notices when redistributing dependencies or a combined work |
| Logo / SVG | Supplied project assets; project records describe logo creation for Blind Pew | No exhaustive image-similarity, trademark or ownership clearance performed |
| Privacy | No network client, telemetry, clipboard read, device hook or typed-text log found in runtime source | Sensitive-field protection depends on the client supplying IBus hints; this is not a blanket regulatory certificate |

Targeted public searches for distinctive source strings returned no relevant
external implementation. Searches included “Bounded, rendered-suffix transducer”,
“Hold only a suffix a later character can still change” and
“Keep desktop settings and their saved originals consistent on failure”.
Search-engine coverage is incomplete; absence of a result is not proof of novelty.
The public name “Blind Pew” refers to a pre-existing literary character; this
review does not establish freedom to use every later visual adaptation or mark.

## Traceable assets

| File | SHA-256 |
|---|---|
| `data/profiles.json` | `43928fa1af9fcbdab79675b91a0f803d60cf8995259ddbe3c2912eb961ab9184` |
| `docs/blind-pew-logo.png` | `5488869d17ce641262171f3c47e851c3fa17ed28d284e7da10d152f9285dcc58` |
| `assets/blind-pew.svg` | `28b84e05f978f71c4c66dd58f045faf24256a911e5e5c31469522a71538c73fc` |

## Sources consulted

- [MIT license, Open Source Initiative](https://opensource.org/license/mit)
- [Translit.ru terms](https://translit.ru/info/disclaimer/)
- [Translit.ru website component licenses](https://translit.ru/info/licenses/)
- [Translit.ru reference behavior](https://translit.ru/)
- [GNOME extension licensing](https://gjs.guide/extensions/review-guidelines/review-guidelines.html#licensing)
- [PyGObject](https://pygobject.gnome.org/), [GTK3](https://docs.gtk.org/gtk3/), [GTK4](https://docs.gtk.org/gtk4/)
- [IBus COPYING](https://github.com/ibus/ibus/blob/main/COPYING)
- [Ayatana COPYING](https://github.com/AyatanaIndicators/libayatana-appindicator/blob/main/COPYING)
- [CJEU C-406/10, official judgment summary](https://curia.europa.eu/jcms/upload/docs/application/pdf/2012-05/cp120053en.pdf)

The CJEU distinguishes program functionality from protected expression; it does
not automatically resolve the status of these extracted tables. Distribution
jurisdictions, commercial arrangements, patent/trademark registration searches
and any correspondence with rights holders are outside the verified evidence.
For a legal determination, provide this inventory and the original source
materials to qualified counsel in the intended distribution jurisdictions.
