# Speekify Release Procedure

This document is the canonical, end-to-end procedure to cut a Speekify release.
The release is **built and published entirely from a local macOS machine**. There
is no GitHub Actions / CI build: the `.github/workflows/release.yml` workflow was
removed on purpose so that nothing runs on GitHub on tag push.

It assumes the code changes are already merged locally and the repository is clean
enough to tag a release.

## Goal

Publish a macOS standalone binary that can be installed without Python or uv, then
make it available through:

- GitHub Releases (artifact hosting only)
- a Homebrew tap
- direct archive download

Current production setup:

- source repository: `OtterlySpaceLabs/speekify` (private)
- public Homebrew tap: `OtterlySpaceLabs/homebrew-speekify`
- public binary asset: a GitHub Release asset attached to `OtterlySpaceLabs/homebrew-speekify`

The public asset distributed to users and Homebrew must always come from the
**tap** release, not the private source release.

## Distribution model

- End users run `speekify` directly from a standalone macOS binary.
- The binary is built `--onedir` (a folder: the launcher plus a sibling
  `_internal/` with the bundled libs), **not** `--onefile`. Onefile re-extracted
  the whole torch/transformers bundle to a temp dir on every launch, so even
  `speekify -v` took 13–20s. With onedir, the first run after install/upgrade is
  ~11s (one-time macOS Gatekeeper scan of the unsigned dylibs), every run after is
  ~0.5s. Do not switch back to `--onefile`.
- First-run model preparation is done with `speekify setup`.
- Direct generation writes WAV files to the current directory unless `--output-dir`
  is given.

## Prerequisites

- A macOS machine with the same architecture as the published archive (currently `arm64`)
- Read/write access to both GitHub repositories
- `gh` authenticated with the `repo` scope
- `uv`, `git`, `curl`, `tar`, `shasum`, and `brew` installed locally
- The source repo open at its root
- The Homebrew tap cloned next to it at `../homebrew-speekify`

## Files involved

- `scripts/build_standalone_macos.sh` — local PyInstaller `--onedir` build + archive
- `scripts/render_homebrew_formula.py` — renders `Formula/speekify.rb` (onedir install)
- `pyproject.toml` — `[project].version`

## Release flow (local only)

### 1. Validate the repository

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
```

Tests and lint must pass.

### 2. Set the version

Bump `[project].version` in `pyproject.toml` to the target version (example `0.1.0`),
commit it, and push the branch:

```bash
git add pyproject.toml
git commit -m "chore(release): bump version to 0.1.0"
git push origin main
```

### 3. Build the archive locally

```bash
./scripts/build_standalone_macos.sh
```

This syncs dev deps, builds the `--onedir` binary with PyInstaller, packages
`dist/speekify-macos-<arch>.tar.gz` (top level: `speekify/` folder + `share/`), and
prints the archive SHA256. Capture it:

```bash
ARCH="$(uname -m)"
ARCHIVE="dist/speekify-macos-${ARCH}.tar.gz"
SHA256="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
echo "$SHA256"
```

### 4. Tag the release

```bash
git tag v0.1.0
git push origin v0.1.0
```

No workflow runs on this push (the CI workflow was removed). The tag is just a
record pointing at the released commit.

### 5. Publish the private source release

```bash
gh release create v0.1.0 "$ARCHIVE" \
  --repo OtterlySpaceLabs/speekify \
  --title "Speekify v0.1.0" \
  --notes "Release notes here"
```

### 6. Publish the public tap release

Because `OtterlySpaceLabs/speekify` is private, Homebrew cannot fetch from it.
Upload the **same** archive to the public tap repo:

```bash
gh release create speekify-v0.1.0 "$ARCHIVE" \
  --repo OtterlySpaceLabs/homebrew-speekify \
  --title "Speekify v0.1.0" \
  --notes "Public binary release for Homebrew install"
```

### 7. Render and publish the Homebrew formula

```bash
uv run python scripts/render_homebrew_formula.py \
  --version 0.1.0 \
  --url https://github.com/OtterlySpaceLabs/homebrew-speekify/releases/download/speekify-v0.1.0/speekify-macos-arm64.tar.gz \
  --sha256 "$SHA256" \
  --homepage https://github.com/OtterlySpaceLabs/speekify \
  --output ../homebrew-speekify/Formula/speekify.rb

cd ../homebrew-speekify
git add Formula/speekify.rb
git commit -m "Update speekify formula to 0.1.0"
git push origin main
cd -
```

The rendered formula installs the onedir folder into `libexec` and symlinks the
launcher into `bin` (`bin.install_symlink libexec/"speekify/speekify"`), so the
launcher finds its sibling `_internal/`. It also installs `share/man/man1/speekify.1`.

Use `uv run python`, not `python` (the local env may not expose `python`).

### 8. Smoke-test the install paths

Homebrew path:

```bash
brew update
brew upgrade speekify   # or: brew install speekify
speekify --version      # first run ~11s (one-time scan), then ~0.5s
speekify --help
```

Direct archive path:

```bash
curl -L -o speekify.tar.gz https://github.com/OtterlySpaceLabs/homebrew-speekify/releases/latest/download/speekify-macos-arm64.tar.gz
tar -xzf speekify.tar.gz
./speekify/speekify --help
```

## Release checklist

- [ ] `pyproject.toml` version is correct, committed, and pushed
- [ ] `uv run pytest` passes
- [ ] `uv run ruff check .` passes
- [ ] archive built locally and SHA256 captured
- [ ] tag `vX.Y.Z` created and pushed
- [ ] private source release published with the archive
- [ ] public tap release `speekify-vX.Y.Z` published with the archive
- [ ] `Formula/speekify.rb` rendered with the public URL and SHA256, committed and pushed
- [ ] `brew upgrade speekify` works and `speekify --version` is correct
- [ ] direct archive runs without a separate Python install

## Rollback

If a published release is wrong, delete both releases, fix locally, and redo:

```bash
gh release delete v0.1.0 --repo OtterlySpaceLabs/speekify --yes || true
gh release delete speekify-v0.1.0 --repo OtterlySpaceLabs/homebrew-speekify --yes || true
git tag -d v0.1.0 || true
git push origin ":refs/tags/v0.1.0" || true
```

## Known limitations

- The release process is macOS-focused and `arm64`-only at the moment.
- The binary is unsigned, so the first launch after each install/upgrade pays a
  one-time macOS Gatekeeper scan.

## Future improvements

- Wrap the steps above in a single local `scripts/release.sh`.
- Add a separate `x86_64` archive if Intel macOS support is needed.
- Codesign + notarize the bundle to remove the one-time first-run scan.
