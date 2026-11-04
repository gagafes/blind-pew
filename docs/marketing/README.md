# GitHub presentation assets

- `social-preview.png`: 1280 × 640 PNG, navy/gold banner based on the existing Blind Pew logo; prepared with OpenAI image-generation assistance. Upload this file in **Settings → General → Social preview**. Committing it alone does not change GitHub's preview setting.
- `transliteration-demo.gif`: an illustration rendered from the real `Composer` output for Belarusian and Ukrainian, with ordinary-input scenes between profiles. It is not a desktop recording or a hardware F12 test. Reproduce with `python3 .github/scripts/render-demo.py` (Pillow and DejaVu Sans required).

Suggested repository description:

> Offline transliteration switcher for Linux. Eight profiles, QWERTY/QWERTZ, F12 toggle. Debian & Ubuntu, GNOME & Xfce.

Suggested topics:

`linux`, `transliteration`, `ibus`, `keyboard`, `input-method`, `debian`, `ubuntu`, `gnome`, `xfce`, `python`, `gtk`, `multilingual`, `qwerty`, `qwertz`

The published v0.1.0-2 tag and DEB remain fixed. CI builds the current main branch and separately rebuilds the published source to verify the distributed DEB.
