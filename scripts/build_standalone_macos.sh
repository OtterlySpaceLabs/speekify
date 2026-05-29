#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

arch="$(uname -m)"
archive_name="speekify-macos-${arch}.tar.gz"

uv sync --group dev
uv run pyinstaller \
  --name speekify \
  --onefile \
  --clean \
  --noconfirm \
  --paths src \
  --collect-all textual \
  --collect-all supertonic \
  --collect-all trafilatura \
  --collect-all transformers \
  --collect-all sentencepiece \
  --collect-all langdetect \
  src/speekify/__main__.py

mkdir -p dist/release
cp dist/speekify dist/release/speekify
mkdir -p dist/release/share/man/man1
cp docs/man/speekify.1 dist/release/share/man/man1/speekify.1
tar -C dist/release -czf "dist/${archive_name}" speekify share
shasum -a 256 "dist/${archive_name}"