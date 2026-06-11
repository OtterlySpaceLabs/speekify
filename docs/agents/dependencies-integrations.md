# Dependencies And Integrations

- External runtime dependencies include `supertonic`, `httpx`, `trafilatura`, `yt-dlp`, `langdetect`, `torch`, `transformers`, `rich`, `typer` (pinned `<0.26` because newer typer vendors click and breaks the click-based CLI error handling), and `click` (imported directly by `speekify.__main__`).
- MCP support is provided by the `mcp` dependency and the `speekify-mcp` entry point in `src/speekify/mcp_server.py`; client-specific setup notes live in `docs/mcp-clients.md`.
- `translation.py` chooses `mps` when available, otherwise CPU, and disables transformers progress output.
- Speech tagging is enabled by default and combines rules-based `<breath>` placement with CardiffNLP sentiment (`cardiffnlp/twitter-xlm-roberta-base-sentiment`) plus rare capped `<sigh>` tags. Sentiment loading fails open to rules-only tagging, and users can request rules-only behavior with `--no-tag-sentiment --no-tag-sigh`.
- `extract.py` uses `yt-dlp` metadata to locate English YouTube subtitles/transcripts and X oEmbed (`publish.x.com/oembed`) to read public X/Twitter status text. Recognized X URLs never fall back to generic article extraction because x.com serves a JavaScript-required error page to plain HTTP clients; oEmbed failures surface as clear extraction errors. Other URLs use trafilatura-based generic extraction, with Medium feed/GraphQL fallbacks for blocked Medium articles.
- `speekify setup` warms the CardiffNLP sentiment backend by default; `setup --skip-sentiment` skips that download/warmup.
- `logging_utils.configure_logger()` quiets noisy Hugging Face/transformers loggers and prunes records older than 14 days.
- Standalone macOS packaging uses PyInstaller through `scripts/build_standalone_macos.sh`; Homebrew formula rendering is handled by `scripts/render_homebrew_formula.py`.
