# Dependencies And Integrations

- External runtime dependencies include `supertonic`, `httpx`, `trafilatura`, `langdetect`, `torch`, `transformers`, `rich`, and `typer`.
- MCP support is provided by the `mcp` dependency and the `speekify-mcp` entry point in `src/speekify/mcp_server.py`; client-specific setup notes live in `docs/mcp-clients.md`.
- `translation.py` chooses `mps` when available, otherwise CPU, and disables transformers progress output.
- Speech tagging is enabled by default and combines rules-based `<breath>` placement with CardiffNLP sentiment (`cardiffnlp/twitter-xlm-roberta-base-sentiment`) plus rare capped `<sigh>` tags. Sentiment loading fails open to rules-only tagging, and users can request rules-only behavior with `--no-tag-sentiment --no-tag-sigh`.
- `speekify setup` warms the CardiffNLP sentiment backend by default; `setup --skip-sentiment` skips that download/warmup.
- `logging_utils.configure_logger()` quiets noisy Hugging Face/transformers loggers and prunes records older than 14 days.
- Standalone macOS packaging uses PyInstaller through `scripts/build_standalone_macos.sh`; Homebrew formula rendering is handled by `scripts/render_homebrew_formula.py`.