# Releasing Blind Pew

The package version comes from `debian/changelog`.
The application version is the part before the Debian revision. User-facing
changes are recorded in [CHANGELOG.md](../CHANGELOG.md).

1. Update the application version and Debian changelog together. A package-only
   revision can keep the application version. Add matching notes at
   `.github/release-notes/v<package-version>.md`.
2. Merge the release source into `main` and wait for **Test and build Blind
   Pew** to pass on that exact commit. Check package and desktop jobs on
   Debian 13 and Ubuntu 24.04, the security job, and package warnings. Use the
   [testing guide](TESTING.md) for the scope and local commands.
3. Inspect the DEB and `SHA256SUMS` from the `blind-pew-ubuntu-24.04` artifact.
   The CI job builds twice and compares bytes, verifies the installed payload
   and tests IBus, upgrade, removal and reinstall. Compare outputs built with
   the same toolchain.
4. When ready to publish, open **Actions → Publish Blind Pew → Run workflow**
   on `main` and enter the successful CI run ID in `ci_run_id`. The workflow
   checks the selected run and release asset, verifies the draft's uploaded
   byte contents, and publishes the matching version tag and release.
   [Publication workflow](https://github.com/gagafes/blind-pew/actions/workflows/publish-release.yml)
5. Confirm the tag, release notes and downloads at the public release page.
   The release contains the DEB and `SHA256SUMS`. Update all five READMEs
   with the new DEB, checksum and release-notes links and the matching
   installation command.
   [Releases](https://github.com/gagafes/blind-pew/releases)

CI downloads the [v0.1.0-2 DEB](https://github.com/gagafes/blind-pew/releases/tag/v0.1.0-2)
for the upgrade test and verifies its SHA-256 against the digest pinned in
`ci.yml`. The Ubuntu job also rebuilds that release from its pinned source
commit and compares the resulting DEB with the published download.

Verify a downloaded package in its own directory:

```sh
sha256sum --check SHA256SUMS
```

For package provenance and how to report issues, see the
[licensing notices](../THIRD_PARTY_NOTICES.md) and [security policy](../SECURITY.md).
