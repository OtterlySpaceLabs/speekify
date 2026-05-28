from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a Homebrew formula for a Speekify standalone release archive."
    )
    parser.add_argument("--version", required=True, help="Release version, for example 0.1.0")
    parser.add_argument("--url", required=True, help="Release tarball URL")
    parser.add_argument("--sha256", required=True, help="SHA256 of the release tarball")
    parser.add_argument(
        "--homepage",
        default="https://github.com/hiboux/speekify",
        help="Project homepage",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output file path. Prints to stdout when omitted.",
    )
    return parser


def render_formula(*, version: str, url: str, sha256: str, homepage: str) -> str:
    return f'''class Speekify < Formula
  desc "French text and URL to WAV converter powered by Supertonic v3"
  homepage "{homepage}"
  url "{url}"
  sha256 "{sha256}"
  version "{version}"

  def install
    bin.install "speekify"
  end

  test do
    assert_match "Genere un fichier WAV", shell_output("#{{bin}}/speekify --help")
    assert_match "Telecharge et prechauffe", shell_output("#{{bin}}/speekify setup --help")
  end
end
'''


def main() -> int:
    args = build_parser().parse_args()
    formula = render_formula(
        version=args.version,
        url=args.url,
        sha256=args.sha256,
        homepage=args.homepage,
    )

    if args.output is None:
        print(formula, end="")
        return 0

    args.output.write_text(formula, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())