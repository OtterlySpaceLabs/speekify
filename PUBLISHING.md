# Publishing Speekify

This is the PyPI-specific overview. The canonical end-to-end checklist for
PyPI and Homebrew is [docs/release-procedure.md](docs/release-procedure.md).

## One-time PyPI setup

Configure a PyPI trusted publisher with:

- project: `speekify`
- GitHub owner/repository: `OtterlySpaceLabs/speekify`
- workflow: `publish.yml`
- environment: `pypi`

Create the matching `pypi` environment in GitHub. No PyPI API-token secret is
needed because `.github/workflows/publish.yml` uses GitHub OIDC.

## Publish a release

Update both version declarations, validate, commit, and push:

```bash
# pyproject.toml: [project].version = "0.2.0"
uv sync --group dev
uv run pytest
uv run ruff check .

git add pyproject.toml uv.lock
git commit -m "chore(release): bump version to 0.2.0"
git push origin main
```

Create and push `v0.2.0`, then publish the GitHub Release. Publishing the
Release triggers two independent workflows:

- `publish.yml` tests, builds and inspects the wheel/sdist, then publishes them
  to PyPI through the trusted publisher.
- `release.yml` builds the arm64 macOS payload used by Homebrew, attaches that
  technical asset, renders `Formula/speekify.rb`, and commits the formula to
  `main`.

The Homebrew payload is not a documented third installation path.

## Verify

Use a clean Python 3.11+ environment:

```bash
python -m venv /tmp/speekify-release-test
/tmp/speekify-release-test/bin/pip install "speekify==0.2.0"
/tmp/speekify-release-test/bin/speekify --version
/tmp/speekify-release-test/bin/speekify --help
/tmp/speekify-release-test/bin/speekify --doctor
```

`--doctor` reports whether the pinned Temporal runtime is already available or
can be provisioned, but does not download it. A clean pip/pipx/uv installation
downloads and verifies Temporal CLI 1.8.1 on its first real generation.
Automatic provisioning supports macOS and Linux on `arm64`/`amd64`; Windows is
not supported.

PyPI releases are immutable. A broken upload requires a new version.
