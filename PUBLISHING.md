# Publishing Speekify

This document explains how to publish Speekify on PyPI.

## Prerequisites

1. GitHub repository with admin access
2. PyPI account (create at https://pypi.org)
3. PyPI trusted publisher configured

## Setup (One-time)

### 1. Configure PyPI Trusted Publisher

On PyPI, add a trusted publisher for this repository:
- Go to https://pypi.org/manage/account/publishing/
- Add a new trusted publisher:
  - PyPI Project Name: `speekify`
  - GitHub Repository Owner: `OtterlySpaceLabs`
  - GitHub Repository Name: `speekify`
  - GitHub Workflow Name: `publish.yml`
  - GitHub Environment Name: `pypi`

### 2. Create GitHub Environment

1. Go to repository Settings → Environments
2. Create new environment named `pypi`
3. No secrets needed (using OIDC token from PyPI)

## Publishing a Release

### 1. Update Version

Update the version in `pyproject.toml`:

```toml
[project]
version = "0.2.0"
```

### 2. Commit and Create Tag

```bash
git add pyproject.toml
git commit -m "chore: bump version to 0.2.0"
git tag v0.2.0
git push origin main v0.2.0
```

### 3. Create Release on GitHub

1. Go to Releases → Draft a new release
2. Select tag `v0.2.0`
3. Set title to `v0.2.0` (or add notes)
4. Click "Publish release"

## What Happens Next

The `publish.yml` workflow will:
1. Build the distribution files (wheel + sdist)
2. Publish to PyPI using OIDC token authentication
3. Create a release asset with build logs

You can monitor progress in Actions tab.

## Verification

After publishing, verify on PyPI:
- https://pypi.org/project/speekify/

Test installation:
```bash
pip install --upgrade speekify
speekify --version
```

## Notes

- The `test.yml` workflow runs on every push/PR to catch issues before publishing
- Both `pip install speekify` and `uv tool install speekify` will work after publishing
- Releases are immutable on PyPI (cannot re-upload same version)
