# Dependencies And Integrations

- External runtime dependencies include `supertonic`, `httpx`, `trafilatura`, `langdetect`, `torch`, `transformers`, `rich`, and `typer`.
- `translation.py` chooses `mps` when available, otherwise CPU, and disables transformers progress output.
- `logging_utils.configure_logger()` quiets noisy Hugging Face/transformers loggers and prunes records older than 14 days.
- Standalone macOS packaging uses PyInstaller through `scripts/build_standalone_macos.sh`; Homebrew formula rendering is handled by `scripts/render_homebrew_formula.py`.