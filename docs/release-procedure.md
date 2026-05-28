# Speekify Release Procedure

This document captures the release and distribution steps for later. It assumes the code changes are already merged locally and that the repository is clean enough to tag a release.

## Goal

Publish a macOS standalone binary that can be installed without Python or uv, then make it available through:

- GitHub Releases
- a Homebrew tap
- direct archive download

## Current distribution model

- End users can run `speekify` directly from a standalone macOS binary.
- The first-run model preparation is done with `speekify setup`.
- Direct CLI generation writes WAV files to the current working directory.
- The TUI still writes files into `output/`.

## Prerequisites

- Access to the `hiboux/speekify` GitHub repository
- Permission to create tags and releases
- A Homebrew tap repository such as `hiboux/homebrew-speekify` or equivalent
- A macOS machine if you want to build and test locally
- `uv` available locally if you build outside GitHub Actions

## Files involved

- `scripts/build_standalone_macos.sh`
- `scripts/render_homebrew_formula.py`
- `.github/workflows/release.yml`

## Recommended release flow

### 1. Validate the repository locally

Run:

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
```

Expected result:

- tests pass
- lint passes

### 2. Choose the release version

Example version:

```text
0.1.0
```

Tag format:

```text
v0.1.0
```

Before tagging, make sure the version in `pyproject.toml` matches the intended release version.

### 3. Create and push the Git tag

Run:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Expected result:

- the GitHub Actions workflow `.github/workflows/release.yml` starts automatically
- the workflow builds `speekify-macos-arm64.tar.gz` or the matching archive for the runner architecture
- the workflow publishes that archive to GitHub Releases

### 4. Wait for the release workflow to finish

After the workflow completes, verify on GitHub that:

- a release exists for the pushed tag
- the standalone archive is attached to the release assets

Asset naming currently follows this pattern:

```text
speekify-macos-arm64.tar.gz
```

If the runner architecture changes, the suffix may be `x86_64` instead of `arm64`.

### 5. Compute or copy the SHA256 of the release archive

If you built locally, use:

```bash
shasum -a 256 dist/speekify-macos-arm64.tar.gz
```

If the archive only exists on GitHub Releases, download it and compute the SHA locally.

Keep the final SHA256 value for the Homebrew formula.

### 6. Render the Homebrew formula

Run:

```bash
python scripts/render_homebrew_formula.py \
  --version 0.1.0 \
  --url https://github.com/hiboux/speekify/releases/download/v0.1.0/speekify-macos-arm64.tar.gz \
  --sha256 <sha256>
```

Optional output to a file:

```bash
python scripts/render_homebrew_formula.py \
  --version 0.1.0 \
  --url https://github.com/hiboux/speekify/releases/download/v0.1.0/speekify-macos-arm64.tar.gz \
  --sha256 <sha256> \
  --output Speekify.rb
```

Expected result:

- a valid Homebrew formula named `Speekify` is generated
- the formula installs the standalone binary into `bin`
- the formula test checks `speekify --help` and `speekify setup --help`

### 7. Publish the Homebrew formula in the tap repository

In the tap repository:

- add or update the formula file, usually `Formula/speekify.rb`
- commit the change
- push to the default branch

At that point, end users can install with:

```bash
brew tap hiboux/speekify
brew install speekify
speekify setup
```

If your tap repository name differs, adjust the `brew tap` command accordingly.

### 8. Smoke-test the install paths

Test both paths when possible.

Homebrew path:

```bash
brew uninstall speekify || true
brew tap hiboux/speekify
brew install speekify
speekify --help
speekify setup --skip-translation
speekify "Bonjour depuis brew"
```

Direct archive path:

```bash
curl -L -o speekify.tar.gz https://github.com/hiboux/speekify/releases/latest/download/speekify-macos-arm64.tar.gz
tar -xzf speekify.tar.gz
./speekify --help
./speekify setup --skip-translation
./speekify "Bonjour depuis l'archive"
```

Expected result:

- the binary starts without Python installed separately
- `speekify setup` warms the models
- direct generation creates a WAV in the current directory

## Optional local build workflow

If you want to build before tagging, run:

```bash
./scripts/build_standalone_macos.sh
```

This script currently:

- syncs dev dependencies
- builds a one-file binary with PyInstaller
- creates a release archive in `dist/`
- prints the SHA256 of the archive

## Release checklist

- [ ] `pyproject.toml` version is correct
- [ ] `uv run pytest` passes
- [ ] `uv run ruff check .` passes
- [ ] tag is pushed
- [ ] GitHub Release asset is published
- [ ] SHA256 is recorded
- [ ] Homebrew formula is generated
- [ ] Homebrew tap is updated
- [ ] `speekify setup` works after install
- [ ] `speekify "Bonjour"` writes a WAV in the current directory

## Known limitations

- The current GitHub Actions workflow publishes the standalone archive, but it does not update the Homebrew tap automatically.
- The release process is currently macOS-focused.
- The exact Homebrew tap repository still needs to be finalized if it does not already exist.

## Future improvements

- Automate formula updates in the Homebrew tap after each tagged release
- Add separate archives for Apple Silicon and Intel macOS if needed
- Add notarization and signing if distribution constraints require it