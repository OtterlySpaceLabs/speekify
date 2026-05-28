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
    return (
        "class Speekify < Formula\n"
        '  desc "French text and URL to WAV converter powered by Supertonic v3"\n'
        f'  homepage "{homepage}"\n'
        f'  url "{url}"\n'
        f'  sha256 "{sha256}"\n'
        f'  version "{version}"\n'
        "\n"
        "  def install\n"
        '    bin.install "speekify"\n'
        "  end\n"
        "\n"
        "  test do\n"
        '    assert_match "Generate a local WAV file", shell_output("#{bin}/speekify --help")\n'
        '    assert_match "Download and warm up", shell_output("#{bin}/speekify setup --help")\n'
        "  end\n"
        "end\n"
    )


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