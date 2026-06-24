#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

arch="$(uname -m)"
archive_name="speekify-macos-${arch}.tar.gz"

uv sync --group dev
# ponytail: --onedir (not --onefile) so launch doesn't re-extract the whole
# torch/transformers bundle to a temp dir on every run; --noupx avoids
# per-launch UPX decompression. Onefile turned `speekify -v` into a 13-20s wait.
uv run pyinstaller \
  --name speekify \
  --onedir \
  --noupx \
  --clean \
  --noconfirm \
  --paths src \
  --copy-metadata speekify \
  --collect-all supertonic \
  --collect-all trafilatura \
  --collect-all transformers \
  --collect-all sentencepiece \
  --collect-all langdetect \
  src/speekify/__main__.py

# ponytail: wipe stale staging first — a leftover dist/release/speekify (esp. an
# old onefile binary as a *file*) makes `cp -R` nest/conflict ("Not a directory").
rm -rf dist/release
mkdir -p dist/release
# onedir produces dist/speekify/ (exe + _internal/), copy the whole folder.
cp -R dist/speekify dist/release/speekify
mkdir -p dist/release/share/man/man1
cp docs/man/speekify.1 dist/release/share/man/man1/speekify.1
tar -C dist/release -czf "dist/${archive_name}" speekify share
shasum -a 256 "dist/${archive_name}"