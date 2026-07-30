# Speekify Release Procedure

This document is the canonical, end-to-end procedure to cut a Speekify release.
The Python distributions and the technical macOS payload consumed by Homebrew
are built by **GitHub Actions**, not on a local machine.

## Goal

Publish the two supported installation paths:

- PyPI (`pip`, `pipx`, or `uv`)
- the Homebrew tap shipped in this repository (`Formula/speekify.rb`)

Current production setup:

- single public repository: `OtterlySpaceLabs/speekify`
- the Homebrew formula lives in this repo under `Formula/`
- the Homebrew-only payload is attached to the GitHub Release of this repo

Because the repo is public, Homebrew fetches its implementation payload straight
from this repo's release — there is no separate tap repo anymore. The payload is
not documented or supported as a third installation method.

## Distribution model

- pip users receive the wheel/sdist. On first generation, Speekify downloads the
  pinned Temporal CLI asset into the user data directory and verifies its SHA-256.
  Automatic provisioning covers macOS/Linux on `arm64`/`amd64`; Windows is not
  supported.
- Homebrew users receive the formula. It declares `depends_on "temporal"`, so
  Homebrew owns that dependency; the Speekify payload never bundles Temporal.
- The Homebrew payload is built `--onedir` (a folder: the launcher plus a sibling
  `_internal/` with the bundled libs), **not** `--onefile`. Onefile re-extracted
  the whole torch/transformers bundle to a temp dir on every launch, so even
  `speekify -v` took 13–20s. With onedir, the first run after install/upgrade is
  ~11s (one-time macOS Gatekeeper scan of the unsigned dylibs), every run after is
  ~0.5s. Do not switch back to `--onefile`.
- First-run model preparation is done with `speekify setup`.

## Files involved

- `.github/workflows/release.yml` — CI build + release + formula update (runs on macOS)
- `scripts/build_homebrew_payload_macos.sh` — builds the private Homebrew payload
- `scripts/render_homebrew_formula.py` — renders `Formula/speekify.rb`
- `pyproject.toml` — `[project].version`

## Release flow

### 1. Bump the version

Update `[project].version` in `pyproject.toml` (and the local `speekify` entry in
`uv.lock`), commit, and push:

```bash
git add pyproject.toml uv.lock
git commit -m "chore(release): bump version to 0.2.0"
git push origin main
```

### 2. Tag and publish a GitHub Release

Create and push the tag, then publish a Release for it:

```bash
git tag v0.2.0
git push origin v0.2.0

gh release create v0.2.0 \
  --title "Speekify v0.2.0" \
  --notes "Release notes here"
```

`gh release create` publishes the release, which triggers two workflows:

- `publish.yml` → builds the wheel/sdist and publishes to PyPI
- `release.yml` → builds the Homebrew payload, attaches it to this release, renders
  `Formula/speekify.rb`, and commits it back to `main`

### 3. What the macOS workflow does (automatic)

On `release: published`, `release.yml` runs on a `macos-latest` (arm64) runner and:

1. builds the formula payload via `scripts/build_homebrew_payload_macos.sh`
2. uploads `speekify-homebrew-macos-arm64.tar.gz` for Homebrew consumption
3. renders the formula with the release asset URL + its SHA256
4. commits `Formula/speekify.rb` to `main` with the bumped version

No local macOS machine is required. Monitor it in the Actions tab.

### 4. Smoke-test the supported install paths

pip path in a clean environment:

```bash
python -m venv /tmp/speekify-release-test
/tmp/speekify-release-test/bin/pip install "speekify==<version>"
/tmp/speekify-release-test/bin/speekify --version
/tmp/speekify-release-test/bin/speekify --help
/tmp/speekify-release-test/bin/speekify --doctor
```

`--doctor` validates platform support without downloading Temporal. A separate
first-generation smoke test is required to exercise the verified Temporal
download and model-backed audio path.

Homebrew path:

```bash
brew update
brew upgrade speekify   # or: brew install speekify
speekify --version      # first run ~11s (one-time scan), then ~0.5s
speekify --help
```

First-time tap (the repo isn't named `homebrew-*`, so pass the URL explicitly):

```bash
brew tap otterlyspacelabs/speekify https://github.com/OtterlySpaceLabs/speekify
brew install speekify
```

## Release checklist

- [ ] `pyproject.toml` / `uv.lock` version bumped, committed, pushed
- [ ] `uv run pytest` and `uv run ruff check .` pass (also enforced by `test.yml`)
- [ ] tag `vX.Y.Z` created and pushed
- [ ] GitHub Release `vX.Y.Z` published
- [ ] `publish.yml` succeeded (PyPI)
- [ ] `release.yml` succeeded: Homebrew payload attached + formula updated on `main`
- [ ] clean pip install can provision the pinned Temporal runtime automatically
- [ ] `brew upgrade speekify` works and `speekify --version` is correct

## Rollback

If a published release is wrong, delete it, fix, and redo:

```bash
gh release delete v0.2.0 --yes || true
git tag -d v0.2.0 || true
git push origin ":refs/tags/v0.2.0" || true
```

If the formula commit on `main` is bad, revert it like any other commit. PyPI
releases are immutable, so a broken PyPI upload requires a new patch version.

## Known limitations

- The Homebrew payload is macOS `arm64`-only (`macos-latest` = Apple Silicon).
  This does not limit the PyPI runtime, which also supports macOS `amd64` and
  Linux `arm64`/`amd64`.
- The binary is unsigned, so the first launch after each install/upgrade pays a
  one-time macOS Gatekeeper scan.
- `release.yml` pushes the formula commit to `main` with `GITHUB_TOKEN`. If `main`
  has branch protection that blocks the Actions bot, the push step will fail —
  allow the bot to push or relax the rule for `Formula/`.

## Future improvements

- Add a separate `x86_64` Homebrew payload if Intel macOS support is needed.
- Codesign + notarize the bundle to remove the one-time first-run scan.
- Add a `brew audit --strict` validation step to the workflow after the upload.
