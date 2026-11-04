# Releasing Blind Pew

The release candidate is **0.1.0-2** (application version **0.1.0**).
Release notes are in [CHANGELOG.md](../CHANGELOG.md); reporting instructions
and the security model are in [SECURITY.md](../SECURITY.md).

1. Update the application version and Debian changelog together. A package-only
   revision may keep the application version. `tools/build.py` reads the Debian
   version and default `SOURCE_DATE_EPOCH` from the changelog and rejects a
   mismatched application version.
2. Run the complete CI suite on the exact source commit. Both target systems,
   the desktop checks and the security job must pass. Review the logs, including
   any package warnings; do not publish a failed or cancelled build.
3. Use the Ubuntu 24.04 CI artifact as the distribution build. The job rebuilds
   it twice and compares the bytes, installs it, exercises it through IBus,
   checks its payload and tests upgrade/removal. Reproducibility is guaranteed
   only for the same toolchain, not different Debian/xz releases.
4. Copy that checked DEB to `downloads/`, update `downloads/SHA256SUMS` and all
   five README download/install links. Run CI on the resulting commit and
   compare the distributed package with the fresh build.
5. Create a GitHub release for the checked commit, named `v0.1.0-2`, with the DEB,
   SHA256SUMS and the matching changelog notes. Keep it a draft until the release
   checks pass. Publishing a tag/release is separate from preparing the repo.

Verify a download from the repository root with:

```sh
(cd downloads && sha256sum --check SHA256SUMS)
sudo apt install ./downloads/blind-pew_0.1.0-2_all.deb
```

The package is architecture-independent Python/GJS and uses system GTK/IBus.
Tests cannot establish behavior in every application: Qt, Electron, Flatpak,
Snap, physical keyboard hardware and all 49 human translations still require
manual coverage. See [TESTING.md](TESTING.md) for the exact automated scope.
